#!/usr/bin/env python3
"""
TapTap 搜索联想 API 查询工具
输入游戏名称，自动调用 /search/v6/agg-search，输出 hits_total 和 fans_count。

用法:
  python tapsearch.py "游戏名称"

签名机制:
  已逆向 TapSignKit 签名算法，使用 HMAC-SHA256 + client_secret 实时生成
  X-Tap-Sign / X-Tap-Nonce / X-Tap-Ts，无需抓包获取认证头。

  client_secret 逆向路径:
    APK resources.arsc → R.string.client_secret (0x7f100039)
    → AES/ECB/PKCS5Padding 解密 (key="CAQt3RD6VsZnzEoF")
    → aOqilgPqN4grnMG5VdLlhLptAU3WHorK

  签名算法来源:
    com.taptap.other.basic.impl.application.features.b.java
    → HMAC-SHA256(client_secret, METHOD\npath?query\nheaders\nbody\n)
"""

import sys
import struct
import requests
import urllib.parse
import time
import base64
import json
import hmac
import hashlib
import random
import uuid

# ============================================================
# 实时签名配置 — 已逆向 TapSignKit 算法，无需抓包
# ============================================================
#
# 算法来源: com.taptap.other.basic.impl.application.features.b.java
# X-Tap-Sign = HMAC-SHA256(
#     client_secret,
#     METHOD + "\n" + /path?query + "\n" +
#     "x-tap-nonce:xxx\n" + "x-tap-ts:xxx\n" +
#     body + "\n"
# )
#
# client_secret 来源: APK resources.arsc R.string.client_secret (0x7f100039)
#   加密值: eVEtpR0UkQvNTyQoGyRYIc7VcPMTlSAhuVAbp2d+05CwSIMc8uFSnwi9lt4Js0Uo
#   解密: AES/ECB/PKCS5Padding(key="CAQt3RD6VsZnzEoF") → aOqilgPqN4grnMG5VdLlhLptAU3WHorK

CLIENT_SECRET = "aOqilgPqN4grnMG5VdLlhLptAU3WHorK"

CONFIG = {
    # --- 固定请求头 ---
    "host": "api.taptapdada.com",
    "accept": "application/x-protobuf",
    "user_agent": (
        "TapTap/2.96.0-rel#100200 (com.taptap; build:296001002; Android 11) "
        "Okhttp/3.12.1"
    ),
    "content_type": (
        'application/x-protobuf; desc="https://pbdesc.xdrnd.cn/apis.desc"; '
        'messageType="apis.clientapi.search.AggSearchV6Request"'
    ),
}


# ============================================================
# Protobuf 编码 (AggSearchV6Request)
# ============================================================

def encode_varint(value):
    buf = bytearray()
    while value > 127:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.append(value & 0x7F)
    return bytes(buf)

def encode_string(tag, value):
    data = value.encode('utf-8')
    return encode_varint((tag << 3) | 2) + encode_varint(len(data)) + data

def encode_uint64(tag, value):
    return encode_varint((tag << 3) | 0) + encode_varint(value)

def build_request(keyword, limit=10):
    """AggSearchV6Request: types(tag2), kw(tag3), scene(tag5), limit(tag7)"""
    return (encode_string(2, "mix") +
            encode_string(3, keyword) +
            encode_string(5, "suggest") +
            encode_uint64(7, limit))


# ============================================================
# Protobuf 解码 (AggSearchV6Response)
# ============================================================

def read_varint(data, offset):
    value, shift = 0, 0
    while offset < len(data):
        byte = data[offset]; value |= (byte & 0x7F) << shift; offset += 1
        if not (byte & 0x80): break
        shift += 7
    return value, offset

def read_ld(data, offset):
    length, offset = read_varint(data, offset)
    return data[offset:offset + length], offset + length

def parse_brand_stat(data):
    off, stat = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 0:
            v, off = read_varint(data, off)
            if t == 4:   stat['hits_total'] = v
            elif t == 5: stat['fans_count'] = v
            elif t == 6: stat['bought_count'] = v
            elif t == 7: stat['reserve_count'] = v
        elif wt == 2: _, off = read_ld(data, off)
        elif wt == 1: off += 8
        elif wt == 5: off += 4
    return stat

def parse_list_app_card(data):
    off, result = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 0:
            v, off = read_varint(data, off)
            if t == 1: result['app_id'] = v
        elif wt == 2:
            r, off = read_ld(data, off)
            if t == 2:
                try: result['package_name'] = r.decode('utf-8')
                except: pass
            elif t == 5:
                try: result['title'] = r.decode('utf-8')
                except: pass
        elif wt == 1: off += 8
        elif wt == 5: off += 4
    return result

def parse_brand(data):
    off, result = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 2:
            r, off = read_ld(data, off)
            if t == 1:  result['app'] = parse_list_app_card(r)
            elif t == 11: result['stat'] = parse_brand_stat(r)
        elif wt == 0: _, off = read_varint(data, off)
        elif wt in (1, 5): off += 8 if wt == 1 else 4
    return result

def parse_mix_item(data):
    off, result = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 0:
            v, off = read_varint(data, off)
            if t == 1: result['index'] = v
        elif wt == 2:
            r, off = read_ld(data, off)
            if t == 2:
                try: result['type'] = r.decode('utf-8')
                except: pass
            elif t == 6:  result['brand'] = parse_brand(r)
            elif t == 9:  result['app'] = parse_list_app_card(r)
        elif wt in (1, 5): off += 8 if wt == 1 else 4
    return result

def unwrap_response(data):
    """Strip outer wrapper + google.protobuf.Any to get AggSearchV6Response."""
    off = 0
    tw, off = read_varint(data, off)
    if (tw >> 3) == 1 and (tw & 7) == 0: _, off = read_varint(data, off)
    tw, off = read_varint(data, off)
    blob, off = read_ld(data, off)
    boff = 0
    tw, boff = read_varint(blob, boff); _, boff = read_ld(blob, boff)
    tw, boff = read_varint(blob, boff); value, _ = read_ld(blob, boff)
    return value

def parse_response(raw_data):
    """AggSearchV6Response → list of result dicts."""
    inner = unwrap_response(raw_data)
    off, results = 0, []
    while off < len(inner):
        tw, off = read_varint(inner, off)
        wt, t = tw & 7, tw >> 3
        if wt == 2:
            agg_item, off = read_ld(inner, off)
            if t == 1:
                aoff = 0
                while aoff < len(agg_item):
                    tw2, aoff = read_varint(agg_item, aoff)
                    wt2, t2 = tw2 & 7, tw2 >> 3
                    if wt2 == 2:
                        r, aoff = read_ld(agg_item, aoff)
                        if t2 == 2:
                            results.append(parse_mix_item(r))
                    elif wt2 == 0: _, aoff = read_varint(agg_item, aoff)
                    elif wt2 in (1, 5): aoff += 8 if wt2 == 1 else 4
        elif wt == 0: _, off = read_varint(inner, off)
        elif wt in (1, 5): off += 8 if wt == 1 else 4
    return results


# ============================================================
# 实时签名生成
# ============================================================

def build_x_ua():
    """生成 X-UA 参数 (与 TapTap Android 客户端格式一致)"""
    date_str = time.strftime("%Y%m%d")
    rnd = ''.join(random.choice(
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    ) for _ in range(12))
    ch = f"organic-direct_index_d{date_str}--{date_str[2:]}{rnd}"
    uid = str(uuid.uuid4())
    return (
        f"V=1&PN=TapTap&VN=2.96.0-rel.100200&VN_CODE=296001002"
        f"&LOC=CN&LANG=zh_CN&CH={ch}&UID={uid}"
        f"&NT=1&SR=1080x2220&DEB=Xiaomi&DEM=Redmi+Note+8+Pro&OSV=11"
    )


def compute_x_tap_sign(method, url_path, query, x_tap_headers, body_bytes):
    """HMAC-SHA256 X-Tap-Sign, 算法来自 b.java"""
    # 收集 x-tap-* 头，按 key 排序 (大小写不敏感)
    x_tap = [(k.lower(), v) for k, v in x_tap_headers.items()
             if k.lower().startswith('x-tap-')]
    x_tap.sort(key=lambda kv: kv[0])
    sorted_headers_str = "\n".join(f"{k}:{v}" for k, v in x_tap)

    path_query = f"{url_path}?{query}"
    signing_str = f"{method}\n{path_query}\n{sorted_headers_str}\n"
    signing_bytes = signing_str.encode('utf-8') + body_bytes + b"\n"

    return base64.b64encode(
        hmac.new(CLIENT_SECRET.encode('utf-8'), signing_bytes, hashlib.sha256).digest()
    ).decode('utf-8')


# ============================================================
# API 调用
# ============================================================

def search(keyword, config=None):
    cfg = config or CONFIG

    # 动态生成 X-UA 和签名
    x_ua = build_x_ua()
    url_path = "/search/v6/agg-search"
    query = f"X-ENC=pb&X-UA={urllib.parse.quote(x_ua, safe='')}"
    url = f"https://api.taptapdada.com{url_path}?{query}"
    body = build_request(keyword)

    ts_str = f"{int(time.time()):010d}"
    nonce = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789')
                    for _ in range(20))

    x_tap_headers = {
        "X-Tap-Nonce": nonce,
        "X-Tap-Ts": ts_str,
    }
    x_tap_sign = compute_x_tap_sign("POST", url_path, query, x_tap_headers, body)

    headers = {
        "Host": cfg["host"],
        "Accept": cfg["accept"],
        "User-Agent": cfg["user_agent"],
        "Content-Type": cfg["content_type"],
        "Content-Length": str(len(body)),
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "X-Tap-Sign": x_tap_sign,
        "X-Tap-Nonce": nonce,
        "X-Tap-Ts": ts_str,
    }

    resp = requests.post(url, data=body, headers=headers, timeout=15)

    if resp.status_code != 200:
        # Try to extract error message from protobuf error response
        try:
            inner = resp.content
            # google.rpc.Status or similar error proto
            if b'INVALID_TIME' in inner or b'invalid time' in inner:
                print(f"[错误] HTTP {resp.status_code} — 时间戳校验失败")
                print(f"  本地时间与服务器时间偏差过大，请检查系统时间。")
            elif b'UNAUTHENTICATED' in inner or b'unauthenticated' in inner:
                print(f"[错误] HTTP {resp.status_code} — 签名验证失败")
                print(f"  client_secret 可能已变更，请重新逆向提取。")
            else:
                print(f"[错误] HTTP {resp.status_code}")
                # Try to find a readable error string
                for i in range(len(inner) - 4):
                    chunk = inner[i:i+50]
                    try:
                        decoded = chunk.decode('ascii')
                        if any(kw in decoded for kw in ['error', 'Error', 'time', 'TIME', 'invalid']):
                            print(f"  {decoded.strip()}")
                    except:
                        pass
        except Exception as e:
            print(f"[错误] HTTP {resp.status_code}: {e}")
        return []

    return parse_response(resp.content)


# ============================================================
# 签名就绪检查
# ============================================================

def check_signing_readiness():
    """Check that client_secret is available and time is reasonable."""
    print("实时签名状态检查:")
    print("-" * 50)
    print(f"  [有效] client_secret 已内置 (逆向提取自 APK resources.arsc)")
    print(f"  [有效] 签名算法: HMAC-SHA256 (来自 TapSignKit / b.java)")
    now = int(time.time())
    print(f"  [信息] 当前时间戳: {now} ({time.strftime('%Y-%m-%d %H:%M:%S')})")
    print()


# ============================================================
# 主程序
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("用法: python tapsearch.py <游戏名称>")
        print("示例: python tapsearch.py 心动小镇")
        print("      python tapsearch.py 最强祖师")
        print()
        print("签名自动生成，无需手动抓包获取认证头。")
        sys.exit(1)

    keyword = sys.argv[1]

    # Check readiness
    check_signing_readiness()

    print(f"搜索: {keyword}")
    print("-" * 50)

    try:
        results = search(keyword)
    except requests.exceptions.ConnectionError:
        print("[网络错误] 无法连接到 api.taptapdada.com")
        print("请检查网络连接和代理设置。")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"[网络错误] {e}")
        sys.exit(1)

    if not results:
        print("未获取到结果 (签名可能已过期，或搜索词无匹配)")
        sys.exit(1)

    for i, item in enumerate(results, 1):
        item_type = item.get('type', '?')

        if 'brand' in item:
            brand = item['brand']
            app = brand.get('app', {})
            stat = brand.get('stat', {})

            print(f"\n[{i}] {app.get('title', 'N/A')}  (brand)")
            print(f"    包名:          {app.get('package_name', 'N/A')}")
            print(f"    ★ hits_total:   {stat.get('hits_total', 0):>12,}")
            print(f"    ★ fans_count:   {stat.get('fans_count', 0):>12,}")
            print(f"    bought_count:   {stat.get('bought_count', 0):>12,}")
            print(f"    reserve_count:  {stat.get('reserve_count', 0):>12,}")

        elif 'app' in item:
            app = item['app']
            print(f"\n[{i}] {app.get('title', 'N/A')}  (app — 无 BrandStat)")

    # Summary
    print("\n" + "=" * 50)
    print("汇总")
    print("=" * 50)
    header = f"  {'游戏':12s}  {'hits_total':>14s}  {'fans_count':>14s}"
    print(header)
    print("  " + "-" * 46)
    for item in results:
        if 'brand' in item:
            brand = item['brand']
            app = brand.get('app', {})
            stat = brand.get('stat', {})
            title = app.get('title', 'N/A')
            hits = stat.get('hits_total', 0)
            fans = stat.get('fans_count', 0)
            print(f"  {title:12s}  {hits:>14,}  {fans:>14,}")


if __name__ == '__main__':
    main()
