#!/usr/bin/env python3
"""
TapTap 搜索数据查询 Web 界面
启动本地服务器，通过浏览器查询游戏数据。

用法:
  python tapserver.py
  然后打开 http://localhost:8888
"""

import sys
import os
import json
import time
import hmac
import hashlib
import base64
import random
import uuid
import urllib.parse
import struct
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

# 复用 tapsearch 的签名和 protobuf 逻辑
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from tapsearch import (
    build_request, parse_response, build_x_ua, compute_x_tap_sign,
    CLIENT_SECRET, CONFIG
)

# ============================================================
# HTML 页面
# ============================================================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TapTap 游戏数据查询</title>
<style>
  :root {
    --bg: #0f0f14;
    --card: #1a1a24;
    --border: #2a2a3a;
    --text: #e0e0e8;
    --muted: #8888a0;
    --accent: #4fc3f7;
    --accent2: #7c4dff;
    --danger: #ff5252;
    --success: #66bb6a;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .header {
    width: 100%;
    max-width: 720px;
    padding: 40px 20px 20px;
    text-align: center;
  }
  .header h1 {
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .header p {
    color: var(--muted);
    margin-top: 6px;
    font-size: 14px;
  }
  .container {
    width: 100%;
    max-width: 720px;
    padding: 0 20px 60px;
  }
  .search-box {
    display: flex;
    gap: 10px;
    margin-bottom: 24px;
  }
  .search-box input {
    flex: 1;
    padding: 12px 18px;
    font-size: 16px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--card);
    color: var(--text);
    outline: none;
    transition: border-color .2s;
  }
  .search-box input:focus {
    border-color: var(--accent);
  }
  .search-box button {
    padding: 12px 28px;
    font-size: 16px;
    font-weight: 600;
    border: none;
    border-radius: 12px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #fff;
    cursor: pointer;
    transition: opacity .2s, transform .1s;
  }
  .search-box button:hover { opacity: 0.9; }
  .search-box button:active { transform: scale(0.97); }
  .search-box button:disabled { opacity: 0.5; cursor: not-allowed; }

  .status {
    text-align: center;
    padding: 20px;
    color: var(--muted);
    font-size: 14px;
  }
  .status.error { color: var(--danger); }

  .result-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: border-color .2s;
  }
  .result-card:hover { border-color: var(--accent); }
  .result-card .title {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 4px;
  }
  .result-card .pkg {
    font-size: 12px;
    color: var(--muted);
    font-family: "SF Mono", "Fira Code", monospace;
    margin-bottom: 14px;
    word-break: break-all;
  }
  .result-card .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
  }
  .stat-item {
    background: var(--bg);
    border-radius: 10px;
    padding: 12px 14px;
    text-align: center;
  }
  .stat-item .label {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }
  .stat-item .value {
    font-size: 22px;
    font-weight: 700;
    color: var(--accent);
  }
  .stat-item .value.fans { color: var(--accent2); }
  .stat-item .value.bought { color: var(--success); }
  .stat-item .value.reserve { color: #ffa726; }

  .summary {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px 24px;
    margin-top: 20px;
  }
  .summary h3 { font-size: 14px; color: var(--muted); margin-bottom: 10px; }
  .summary table { width: 100%; border-collapse: collapse; }
  .summary th, .summary td {
    text-align: right;
    padding: 8px 12px;
    font-size: 14px;
  }
  .summary th { color: var(--muted); font-weight: 500; border-bottom: 1px solid var(--border); }
  .summary td:first-child, .summary th:first-child { text-align: left; }
  .summary tr:not(:last-child) td { border-bottom: 1px solid rgba(255,255,255,.03); }

  .note {
    text-align: center;
    color: var(--muted);
    font-size: 11px;
    margin-top: 10px;
    padding: 12px;
  }
  .spinner {
    display: inline-block;
    width: 20px; height: 20px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin .6s linear infinite;
    vertical-align: middle;
    margin-right: 8px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<div class="header">
  <h1>TapTap 游戏数据查询</h1>
  <p>输入游戏名称，查询 PC 端完整数据（总下载量 / 移动端 / PC端 / 评分 / 发布日期）</p>
</div>

<div class="container">
  <div class="search-box">
    <input id="keyword" type="text" placeholder="输入游戏名称，如 心动小镇、原神…"
           autofocus autocomplete="off">
    <button id="search-btn" onclick="doSearch()">搜索</button>
  </div>

  <div id="results"></div>
  <div class="note">
    &copy; 2026 雪球@月旨_投资笔记 &nbsp;|&nbsp; 仅供学习研究
  </div>
</div>

<script>
const input = document.getElementById('keyword');
const btn = document.getElementById('search-btn');
const results = document.getElementById('results');

input.addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

function formatNum(n) {
  if (n === undefined || n === null) return '-';
  return Number(n).toLocaleString('zh-CN');
}

function doSearch() {
  const kw = input.value.trim();
  if (!kw) return;

  btn.disabled = true;
  results.innerHTML = '<div class="status"><span class="spinner"></span>查询中…</div>';

  fetch('/api/pc-detail?q=' + encodeURIComponent(kw))
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        results.innerHTML = `<div class="status error">${data.error}</div>`;
        return;
      }

      let html = '';
      const name = data.game_name || 'N/A';
      const appId = data.app_id || '';

      html += `<div class="result-card" style="border-color: var(--accent);">
        <div class="title" style="font-size:22px; margin-bottom:6px;">${escHtml(name)}</div>
        <div class="pkg">App ID: ${escHtml(appId)}</div>
        <div class="stats" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));">
          <div class="stat-item">
            <div class="label">总下载量 (全平台)</div>
            <div class="value">${formatNum(data.total_downloads)}</div>
          </div>
          <div class="stat-item">
            <div class="label">移动端下载量</div>
            <div class="value fans">${formatNum(data.mobile_downloads)}</div>
          </div>
          <div class="stat-item">
            <div class="label">PC端下载量</div>
            <div class="value bought" style="color: var(--success);">${formatNum(data.pc_downloads)}</div>
          </div>
          <div class="stat-item">
            <div class="label">评分</div>
            <div class="value reserve">${data.rating_score || '-'}</div>
          </div>
          <div class="stat-item">
            <div class="label">评价数量</div>
            <div class="value">${formatNum(data.rating_count)}</div>
          </div>
          <div class="stat-item">
            <div class="label">发布日期</div>
            <div class="value" style="font-size:16px;">${data.publish_date || '-'}</div>
          </div>
        </div>
      </div>`;

      results.innerHTML = html;
    })
    .catch(err => {
      results.innerHTML = `<div class="status error">网络错误: ${escHtml(err.message)}</div>`;
    })
    .finally(() => {
      btn.disabled = false;
    });
}

function escHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}
</script>
</body>
</html>"""


# ============================================================
# HTTP 服务器
# ============================================================

class TapServer(BaseHTTPRequestHandler):
    """处理 HTTP 请求: / 返回页面, /api/search?q= 移动端查询, /api/pc-detail?q= PC 详情查询"""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        if path == '/':
            self._serve_html()
        elif path == '/api/search':
            self._handle_search(urllib.parse.parse_qs(parsed.query))
        elif path == '/api/pc-detail':
            self._handle_pc_detail(urllib.parse.parse_qs(parsed.query))
        elif path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)

    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode('utf-8'))

    def _handle_search(self, query_params):
        keyword = (query_params.get('q', [''])[0] or
                   query_params.get('keyword', [''])[0]).strip()

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if not keyword:
            resp = {"error": "请输入游戏名称"}
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        try:
            results = _call_tap_search(keyword)
            resp = {"results": results}
        except requests.exceptions.ConnectionError:
            resp = {"error": "无法连接到 api.taptapdada.com，请检查网络"}
        except requests.exceptions.Timeout:
            resp = {"error": "请求超时，请重试"}
        except Exception as e:
            resp = {"error": f"查询失败: {e}"}

        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))

    def _handle_pc_detail(self, query_params):
        keyword = (query_params.get('q', [''])[0] or
                   query_params.get('keyword', [''])[0]).strip()

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if not keyword:
            resp = {"error": "请输入游戏名称"}
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        try:
            resp = _fetch_pc_detail(keyword)
        except requests.exceptions.ConnectionError:
            resp = {"error": "无法连接网络，请检查网络"}
        except requests.exceptions.Timeout:
            resp = {"error": "请求超时，请重试"}
        except Exception as e:
            resp = {"error": f"查询失败: {e}"}

        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        # 只打印 /api/ 请求，不打印静态资源和错误日志
        request_line = str(args[0]) if args else ''
        if '/api/' not in request_line:
            return
        try:
            msg = f"  [{time.strftime('%H:%M:%S')}] {request_line}"
            sys.stdout.buffer.write((msg + '\n').encode('utf-8'))
            sys.stdout.buffer.flush()
        except Exception:
            pass


def _call_tap_search(keyword):
    """调用 TapTap 搜索 API，返回解析后的结果列表"""
    cfg = CONFIG

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
        raise Exception(f"API 返回 HTTP {resp.status_code}")

    return parse_response(resp.content)


# ============================================================
# PC 游戏详情爬取
# ============================================================

WEB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _crawl_pc_detail(app_id):
    """爬取 PC 游戏详情页，从 JSON-LD 提取数据。返回字段字典。"""
    url = f"https://www.taptap.cn/app/{app_id}?os=pc"
    try:
        resp = requests.get(url, headers=WEB_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string)
                if isinstance(ld, dict) and ld.get("@type") == "VideoGame":
                    data = {}
                    data["game_name"] = ld.get("name", "N/A")
                    raw_date = ld.get("datePublished", "")
                    data["publish_date"] = (str(raw_date).split("T")[0] if raw_date else "N/A")
                    interaction = ld.get("interactionStatistic", {})
                    data["total_downloads"] = interaction.get("userInteractionCount", "N/A")
                    aggregate = ld.get("aggregateRating", {})
                    data["rating_score"] = aggregate.get("ratingValue", "N/A")
                    data["rating_count"] = aggregate.get("ratingCount", "N/A")
                    return data
            except (json.JSONDecodeError, TypeError):
                continue
        return {"game_name": "N/A", "publish_date": "N/A", "total_downloads": "N/A",
                "rating_score": "N/A", "rating_count": "N/A"}
    except requests.exceptions.RequestException:
        return {"game_name": "N/A", "publish_date": "N/A", "total_downloads": "N/A",
                "rating_score": "N/A", "rating_count": "N/A"}


def _fetch_pc_detail(keyword):
    """组合搜索 + PC详情爬取 + 移动端查询，返回完整数据。

    1. 使用 tapsearch API 搜索游戏名称，获取 app_id 和移动端数据
    2. 爬取 PC 详情页 (JSON-LD) 获取总下载量等
    3. 计算 PC 端下载量 = 总下载量 - 移动端下载量
    """
    # Step 1: Search via tapsearch API
    try:
        search_results = _call_tap_search(keyword)
    except Exception as e:
        return {"error": f"搜索 API 调用失败: {e}"}

    if not search_results:
        return {"error": f"未找到与「{keyword}」相关的游戏"}

    # Find best match: prefer brand results with matching title
    best = None
    for item in search_results:
        if "brand" in item:
            app = item["brand"].get("app", {})
            stat = item["brand"].get("stat", {})
            app_id = app.get("app_id", "")
            title = app.get("title", "")
            hits = stat.get("hits_total", 0)
            if app_id and title:
                best = (str(app_id), title, hits)
                # Prefer exact match
                if title == keyword or keyword in title:
                    break

    if not best:
        for item in search_results:
            if "app" in item:
                app = item["app"]
                app_id = app.get("app_id", "")
                title = app.get("title", "")
                if app_id and title:
                    best = (str(app_id), title, 0)
                    break

    if not best:
        return {"error": f"未找到与「{keyword}」相关的游戏"}

    app_id, game_name, mobile_downloads = best

    # Step 2: Crawl PC detail page
    detail = _crawl_pc_detail(app_id)

    # Step 3: Calculate PC downloads
    total_str = str(detail.get("total_downloads", "0")).replace(",", "").strip()
    pc_downloads = "N/A"
    try:
        total_dl = int(total_str)
        pc_dl = total_dl - mobile_downloads
        pc_downloads = max(0, pc_dl)
    except (ValueError, TypeError):
        pass

    return {
        "game_name": detail.get("game_name") or game_name,
        "app_id": app_id,
        "total_downloads": detail.get("total_downloads", "N/A"),
        "publish_date": detail.get("publish_date", "N/A"),
        "rating_count": detail.get("rating_count", "N/A"),
        "rating_score": detail.get("rating_score", "N/A"),
        "mobile_downloads": mobile_downloads,
        "pc_downloads": pc_downloads,
    }


# ============================================================
# 入口
# ============================================================

def main():
    port = int(os.environ.get("PORT", 8888))
    server = HTTPServer(('0.0.0.0', port), TapServer)
    url = f"http://localhost:{port}"
    print(f"""
══════════════════════════════════════════
     TapTap 游戏数据查询 Web 界面            
                                          
  地址: {url}                             
  按 Ctrl+C 停止服务器                    
══════════════════════════════════════════
""")
    # 自动打开浏览器（后台线程，避免阻塞服务器启动）
    try:
        import webbrowser
        import threading
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止。")
        server.shutdown()


if __name__ == '__main__':
    main()
