#!/usr/bin/env python3
"""
TapTap PC 游戏全量爬虫 (数据库版)
===================================
本地 SQLite 数据库存储游戏链接与爬取进度，控制台交互式菜单驱动。

数据库: output/taptap_pc.db
  - games 表: 以 app_id 为主键，记录详情页链接、名称、各阶段爬取数据

用法:
  python crawl_pc_games.py    # 交互式菜单
  python crawl_pc_games.py --auto   # 全量自动运行 (非交互)
"""

import os
import sys
import re
import sqlite3
import json
import time
import random
import argparse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from tapsearch import search as tapsearch_search

# ============================================================
# 路径 & 常量
# ============================================================

BASE_URL = "https://www.taptap.cn"
LIST_URL_TEMPLATE = "https://www.taptap.cn/pc/list?page={page}"
HTML_DIR = Path(__file__).parent / "html"
OUTPUT_DIR = Path(__file__).parent / "output"
DB_PATH = OUTPUT_DIR / "taptap_pc.db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

STAGE_LABELS = {
    "new":              "待爬取",
    "detail_crawled":   "详情已爬",
    "mobile_queried":   "移动端已查",
    "complete":         "已完成",
}

# ============================================================
# 数据库操作
# ============================================================

def init_db():
    """初始化数据库和表结构。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            app_id           TEXT PRIMARY KEY,
            game_name        TEXT DEFAULT '',
            detail_url       TEXT NOT NULL,
            total_downloads  TEXT DEFAULT '',
            publish_date     TEXT DEFAULT '',
            rating_count     TEXT DEFAULT '',
            rating_score     TEXT DEFAULT '',
            mobile_downloads TEXT DEFAULT '',
            pc_downloads     TEXT DEFAULT '',
            status           TEXT DEFAULT 'new',
            created_at       TEXT DEFAULT '',
            updated_at       TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def db_upsert_game(conn, app_id, detail_url, game_name=""):
    """插入或忽略游戏链接（以 app_id 去重）。返回 True 表示新增。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute("SELECT app_id FROM games WHERE app_id = ?", (app_id,))
    if cur.fetchone():
        return False  # 已存在
    conn.execute(
        """INSERT INTO games (app_id, detail_url, game_name, status, created_at, updated_at)
           VALUES (?, ?, ?, 'new', ?, ?)""",
        (app_id, detail_url, game_name, now, now),
    )
    conn.commit()
    return True


def db_update_game_detail(conn, app_id, game_name, publish_date,
                          total_downloads, rating_count, rating_score):
    """更新详情页爬取数据。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """UPDATE games SET game_name=?, publish_date=?, total_downloads=?,
           rating_count=?, rating_score=?, status='detail_crawled', updated_at=?
           WHERE app_id=?""",
        (str(game_name), str(publish_date), str(total_downloads),
         str(rating_count), str(rating_score), now, app_id),
    )
    conn.commit()


def db_update_mobile(conn, app_id, mobile_downloads, pc_downloads):
    """更新移动端下载量和 PC 端下载量。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """UPDATE games SET mobile_downloads=?, pc_downloads=?,
           status='mobile_queried', updated_at=?
           WHERE app_id=?""",
        (str(mobile_downloads), str(pc_downloads), now, app_id),
    )
    conn.commit()


def db_get_games_by_status(conn, status):
    """按状态获取游戏列表。"""
    cur = conn.execute(
        "SELECT app_id, game_name, detail_url FROM games WHERE status=? ORDER BY created_at",
        (status,),
    )
    return cur.fetchall()


def db_get_all_games(conn):
    """获取全部游戏。"""
    cur = conn.execute(
        "SELECT app_id, game_name, detail_url, status, total_downloads, "
        "publish_date, rating_count, rating_score, mobile_downloads, pc_downloads "
        "FROM games ORDER BY created_at"
    )
    return cur.fetchall()


def db_count_by_status(conn):
    """统计各状态游戏数量。"""
    cur = conn.execute(
        "SELECT status, COUNT(*) FROM games GROUP BY status"
    )
    return dict(cur.fetchall())


def db_total_count(conn):
    cur = conn.execute("SELECT COUNT(*) FROM games")
    return cur.fetchone()[0]


def extract_app_id_from_url(url):
    """从详情页 URL 提取 app_id。"""
    m = re.search(r"/app/(\d+)", url)
    return m.group(1) if m else None


# ============================================================
# 步骤 1: 下载列表页
# ============================================================

def download_listing_pages(start_page=1, end_page=174):
    """下载 PC 游戏列表页 HTML。"""
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for page in range(start_page, end_page + 1):
        filepath = HTML_DIR / f"pc_list_page_{page}.html"
        if filepath.exists():
            print(f"  [跳过] 第 {page:>3} 页已存在")
            saved.append(str(filepath))
            continue
        url = LIST_URL_TEMPLATE.format(page=page)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            filepath.write_text(resp.text, encoding="utf-8")
            print(f"  [OK]   第 {page:>3} 页已保存")
            saved.append(str(filepath))
        except requests.exceptions.RequestException as e:
            print(f"  [失败] 第 {page:>3} 页: {e}")
        time.sleep(random.uniform(0.5, 1.5))
    return saved


# ============================================================
# 步骤 2: 提取链接并入库
# ============================================================

def extract_and_store_links(listing_files=None):
    """从列表页 HTML 提取 PC 游戏详情链接，去重后写入数据库。"""
    conn = init_db()

    if listing_files is None:
        listing_files = sorted(
            str(p) for p in HTML_DIR.glob("pc_list_page_*.html")
        )

    if not listing_files:
        print("  未找到列表页 HTML 文件，请先执行步骤 1。")
        conn.close()
        return 0, 0

    total_found = 0
    new_count = 0
    seen_this_run = set()

    for filepath in listing_files:
        try:
            html = Path(filepath).read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                m = re.match(r"^/app/(\d+)\?os=pc$", href)
                if not m:
                    continue
                app_id = m.group(1)
                if app_id in seen_this_run:
                    continue
                seen_this_run.add(app_id)
                total_found += 1

                detail_url = f"{BASE_URL}/app/{app_id}?os=pc"
                # 尝试从链接附近获取游戏名称
                game_name = a_tag.get_text(strip=True) or ""
                if db_upsert_game(conn, app_id, detail_url, game_name):
                    new_count += 1
        except Exception as e:
            print(f"  [警告] 解析 {filepath} 失败: {e}")

    conn.close()
    return total_found, new_count


# ============================================================
# 步骤 3: 爬取详情页
# ============================================================

def crawl_detail_page(url):
    """爬取单个游戏详情页，返回数据字典。"""
    data = {
        "game_name": "获取失败",
        "publish_date": "获取失败",
        "total_downloads": "获取失败",
        "rating_count": "获取失败",
        "rating_score": "获取失败",
    }
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string)
                if isinstance(ld, dict) and ld.get("@type") == "VideoGame":
                    data["game_name"] = ld.get("name", "未找到")
                    raw_date = ld.get("datePublished", "")
                    if raw_date:
                        data["publish_date"] = str(raw_date).split("T")[0].split(" ")[0]
                    interaction = ld.get("interactionStatistic", {})
                    data["total_downloads"] = interaction.get("userInteractionCount", "未找到")
                    aggregate = ld.get("aggregateRating", {})
                    data["rating_score"] = aggregate.get("ratingValue", "未找到")
                    data["rating_count"] = aggregate.get("ratingCount", "未找到")
                    break
            except (json.JSONDecodeError, TypeError):
                continue
    except requests.exceptions.RequestException as e:
        print(f"    [请求失败] {e}")
    return data


def crawl_all_detail_pages():
    """从数据库读取全部游戏链接，逐个爬取详情页并更新数据。"""
    conn = init_db()
    cur = conn.execute(
        "SELECT app_id, game_name, detail_url FROM games ORDER BY created_at"
    )
    games = cur.fetchall()
    conn.close()

    if not games:
        print("  数据库中没有游戏链接，请先执行阶段 2。")
        return

    total = len(games)
    print(f"  数据库共 {total} 款，开始爬取详情页...")
    for i, (app_id, old_name, url) in enumerate(games, 1):
        print(f"  [{i:>4}/{total}] {url}")
        data = crawl_detail_page(url)

        conn = init_db()
        db_update_game_detail(
            conn, app_id,
            data["game_name"], data["publish_date"],
            data["total_downloads"], data["rating_count"], data["rating_score"],
        )
        conn.close()

        status = "[OK]" if data["game_name"] != "获取失败" else "[失败]"
        print(f"    {status} 名称:{data['game_name']} | "
              f"下载:{data['total_downloads']} | 评分:{data['rating_score']}")
        time.sleep(random.uniform(0.8, 2.0))


# ============================================================
# 步骤 4: 查询移动端下载量
# ============================================================

def query_mobile_downloads(game_name):
    """使用 tapsearch 查询移动端 hits_total。"""
    try:
        results = tapsearch_search(game_name)
        if not results:
            return 0
        # 精确匹配优先
        for item in results:
            if "brand" in item:
                app = item["brand"].get("app", {})
                stat = item["brand"].get("stat", {})
                if app.get("title", "") == game_name:
                    return stat.get("hits_total", 0)
        # 包含匹配
        for item in results:
            if "brand" in item:
                app = item["brand"].get("app", {})
                stat = item["brand"].get("stat", {})
                title = app.get("title", "")
                if game_name in title or title in game_name:
                    return stat.get("hits_total", 0)
        # 第一个非零
        for item in results:
            if "brand" in item:
                hits = item["brand"].get("stat", {}).get("hits_total", 0)
                if hits > 0:
                    return hits
        return 0
    except Exception as e:
        print(f"      [tapsearch 错误] {game_name}: {e}")
        return 0


def query_all_mobile_downloads():
    """为已爬取详情页但未查移动端的游戏查询移动端下载量。"""
    conn = init_db()
    games = db_get_games_by_status(conn, "detail_crawled")
    conn.close()

    if not games:
        print("  没有待查询移动端下载量的游戏。")
        return

    total = len(games)
    print(f"  共 {total} 款待查询")
    for i, (app_id, name, url) in enumerate(games, 1):
        print(f"  [{i:>4}/{total}] 查询: {name}")
        hits = query_mobile_downloads(name)
        print(f"    hits_total: {hits:,}")

        # 计算 PC 端下载量
        conn = init_db()
        cur = conn.execute(
            "SELECT total_downloads FROM games WHERE app_id=?", (app_id,)
        )
        row = cur.fetchone()
        total_str = str(row[0]).replace(",", "").replace(" ", "") if row else "0"
        try:
            total_dl = int(total_str)
            pc = total_dl - hits
        except (ValueError, TypeError):
            pc = "N/A"
        db_update_mobile(conn, app_id, hits, pc)
        conn.close()
        time.sleep(random.uniform(0.5, 1.5))


# ============================================================
# 步骤 5 & 6: 导出 Excel + HTML
# ============================================================

def export_excel():
    """从数据库导出全部游戏数据到 Excel。"""
    conn = init_db()
    rows = db_get_all_games(conn)
    conn.close()

    if not rows:
        print("  数据库中无数据。")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_taptap_pc_games.xlsx"
    filepath = OUTPUT_DIR / filename

    data = []
    for r in rows:
        data.append({
            "详情页链接": r[2],
            "游戏名称": r[1] or "获取失败",
            "发布日期": r[5] or "获取失败",
            "总下载量": r[4] or "获取失败",
            "评价量": r[6] or "获取失败",
            "评分": r[7] or "获取失败",
            "移动端下载量": r[8] or "获取失败",
            "PC端下载量": r[9] or "获取失败",
        })

    df = pd.DataFrame(data)
    columns_order = [
        "详情页链接", "游戏名称", "发布日期",
        "总下载量", "评价量", "评分",
        "移动端下载量", "PC端下载量",
    ]
    df = df[[c for c in columns_order if c in df.columns]]
    df.to_excel(str(filepath), index=False)
    print(f"  已保存: {filepath}")
    return str(filepath)


def export_html(excel_path=None):
    """从 Excel 生成可排序 HTML 网页。"""
    if excel_path is None:
        excels = sorted(OUTPUT_DIR.glob("*_taptap_pc_games.xlsx"))
        if not excels:
            print("  未找到 Excel 文件，请先执行步骤 5。")
            return
        excel_path = str(excels[-1])

    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日")
    time_prefix = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{time_prefix}_pc_game_ranking.html"
    output_path = OUTPUT_DIR / filename

    page_title = f"TapTap平台PC端游戏下载量明细表（数据截至{today_str}）"

    df = pd.read_excel(excel_path)

    if "详情页链接" in df.columns:
        df["详情页链接"] = df["详情页链接"].apply(
            lambda x: f'<a href="{x}" target="_blank">点击访问</a>'
            if pd.notnull(x) and str(x) not in ("获取失败", "nan")
            else ""
        )

    table_html = df.to_html(
        index=False, classes="styled-table", table_id="dataTable", escape=False
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #f0f2f5; margin: 0; padding: 40px 20px; }}
        h2 {{ text-align: center; color: #1a1a1a; font-size: 24px; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 0.9em; }}
        .table-container {{ overflow-x: auto; background: #fff; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.05); padding: 25px; margin: 0 auto; max-width: 98%; }}
        .styled-table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
        .styled-table thead tr {{ background: #2f3542; color: #fff; }}
        .styled-table th, .styled-table td {{ padding: 14px 10px; text-align: center; border-bottom: 1px solid #ececec; }}
        .styled-table th {{ cursor: pointer; user-select: none; transition: background 0.2s; white-space: nowrap; }}
        .styled-table th:hover {{ background: #57606f; }}
        .styled-table tbody tr:nth-of-type(even) {{ background: #f8f9fa; }}
        .styled-table tbody tr:hover {{ background: #e9ecef; }}
        a {{ color: #00a8ff; text-decoration: none; font-weight: 500; }}
    </style>
</head>
<body>
    <h2>{page_title}</h2>
    <div class="subtitle">Click column headers to sort (ascending/descending)</div>
    <div class="table-container">{table_html}</div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const table = document.getElementById('dataTable');
            const headers = table.querySelectorAll('th');
            const tbody = table.querySelector('tbody');
            let sortAsc = new Array(headers.length).fill(true);
            headers.forEach((header, index) => {{
                header.addEventListener('click', () => {{
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    const isAscending = sortAsc[index];
                    rows.sort((rowA, rowB) => {{
                        let cellA = rowA.children[index].innerText.trim();
                        let cellB = rowB.children[index].innerText.trim();
                        let numA = parseFloat(cellA.replace(/,/g, ''));
                        let numB = parseFloat(cellB.replace(/,/g, ''));
                        if (!isNaN(numA) && !isNaN(numB))
                            return isAscending ? numA - numB : numB - numA;
                        return isAscending ? cellA.localeCompare(cellB, 'zh-CN') : cellB.localeCompare(cellA, 'zh-CN');
                    }});
                    sortAsc[index] = !isAscending;
                    headers.forEach(th => th.innerHTML = th.innerHTML.replace(' ▲', '').replace(' ▼', ''));
                    header.innerHTML += isAscending ? ' ▲' : ' ▼';
                    tbody.append(...rows);
                }});
            }});
        }});
    </script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"  已生成: {output_path}")
    return str(output_path)


# ============================================================
# 查看数据库
# ============================================================

def view_database(page=1, page_size=30):
    """分页查看数据库中保存的游戏详情页链接。"""
    conn = init_db()
    total = db_total_count(conn)
    stats = db_count_by_status(conn)

    if total == 0:
        print("  数据库中暂无数据。")
        conn.close()
        return

    total_pages = (total + page_size - 1) // page_size
    offset = (page - 1) * page_size

    cur = conn.execute(
        """SELECT app_id, game_name, detail_url, status, total_downloads,
           mobile_downloads, pc_downloads, updated_at
           FROM games ORDER BY created_at LIMIT ? OFFSET ?""",
        (page_size, offset),
    )
    rows = cur.fetchall()
    conn.close()

    label_map = {"new": "待爬", "detail_crawled": "详情已爬",
                 "mobile_queried": "移动已查", "complete": "已完成"}

    print()
    print("  " + "-" * 50)
    print("  数据库概览")
    for st in ("new", "detail_crawled", "mobile_queried", "complete"):
        cnt = stats.get(st, 0)
        print(f"    {label_map[st]}：{cnt:>5} 款")
    print(f"    合计：{total:>5} 款")
    print("  " + "-" * 50)

    print(f"\n  游戏列表（第 {page}/{total_pages} 页，共 {total} 款）")
    print("  " + "-" * 65)
    # 用制表符对齐，避免中英文混合宽度问题
    print(f"  {'#':<6s}{'App ID':<12s}{'名称':<20s}{'状态':<12s}{'总下载量':>10s}")
    print("  " + "-" * 65)

    for i, (app_id, name, url, status, td, md, pd, ut) in enumerate(rows, offset + 1):
        st_label = label_map.get(status, status)
        display_name = name or "(未获取)"
        # 简单截断
        if len(display_name) > 12:
            display_name = display_name[:11] + ".."
        td_display = str(td) if td else "-"
        if len(td_display) > 12:
            td_display = td_display[:11] + "."
        print(f"  {i:<6d}{app_id:<12s}{display_name:<20s}{st_label:<12s}{td_display:>10s}")

    print("  " + "-" * 65)

    if page < total_pages:
        print(f"  输入 V {page+1} 查看下一页")
    if page > 1:
        print(f"  输入 V {page-1} 查看上一页")


# ============================================================
# 控制台 UI 工具
# ============================================================

def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")


# ----------------------------------------------------------
# 中文排版辅助
# ----------------------------------------------------------

# ----------------------------------------------------------
# 程序说明
# ----------------------------------------------------------

def print_full_screen():
    """一次性打印程序说明 + 数据库状态 + 功能菜单。"""

    conn = init_db()
    stats = db_count_by_status(conn)
    total = db_total_count(conn)
    conn.close()

    t = {
        "total": total,
        "new": stats.get("new", 0),
        "detail": stats.get("detail_crawled", 0),
        "mobile": stats.get("mobile_queried", 0),
    }

    def bar():
        print("  " + "=" * 62)

    def hdr(text):
        bar()
        print(f"   {text}")
        bar()

    def sec(text):
        print(f"\n  {text}")
        print("  " + "-" * 62)

    def item(text):
        print(f"    {text}")

    # ============================================================
    hdr("TapTap PC 游戏全量爬虫 v2.0（数据库版）")

    # ============================================================
    sec("【程序原理】")
    item("通过 TapTap 网页版爬取 PC 端游戏数据，结合 tapsearch")
    item("签名 API 查询移动端下载量，计算出 PC 端下载量，最终")
    item("生成 Excel 表格和可排序 HTML 网页。")
    item("")
    item("数据存储：本地 SQLite 数据库（output/taptap_pc.db）")
    item("去重机制：以 app_id 为主键，重复链接自动跳过")
    item("断点续传：各阶段独立运行，中断后可单独重试")

    # ============================================================
    sec("【数据库状态】")
    item(f"总收录: {t['total']:>5} 款    待爬取: {t['new']:>5} 款    "
         f"详情已爬: {t['detail']:>5} 款    移动已查: {t['mobile']:>5} 款")

    # ============================================================
    sec("【功能菜单】")
    item("[1] 下载列表页       - 从 TapTap 下载第 1~174 页 HTML")
    item("[2] 提取链接并入库   - 解析 HTML，去重写入数据库")
    item("[3] 爬取详情页       - 读取 DB 全部链接，爬取详情数据")
    item("[4] 查询移动端下载量 - 调用 tapsearch 签名 API")
    item("[5] 导出 Excel       - 带日期时间前缀")
    item("[6] 生成 HTML 网页   - 可排序可视化表格")
    item("[7] 一键全流程       - 依次执行 1 -> 2 -> 3 -> 4 -> 5 -> 6")

    # ============================================================
    sec("【其他】")
    item("[V] 查看数据库       - 分页浏览已收录游戏")
    item("[Q] 退出程序")

    print()
    bar()
    print()


# ----------------------------------------------------------
def show_db_status():
    """简短显示数据库状态。"""
    conn = init_db()
    stats = db_count_by_status(conn)
    total = db_total_count(conn)
    conn.close()
    print(f"  [状态] 总收录: {total} | "
          f"待爬: {stats.get('new', 0)} | "
          f"详情已爬: {stats.get('detail_crawled', 0)} | "
          f"移动已查: {stats.get('mobile_queried', 0)}")


# ============================================================
# 阶段执行包装器
# ============================================================

def run_stage_1():
    print()
    print("  " + "=" * 60)
    print("  阶段 1：下载列表页（page 1 ~ 174）")
    print("  " + "=" * 60)
    saved = download_listing_pages(1, 174)
    print(f"\n  共下载/找到 {len(saved)} 个列表页文件\n")


def run_stage_2():
    print()
    print("  " + "=" * 60)
    print("  阶段 2：提取详情页链接并写入数据库")
    print("  " + "=" * 60)
    total, new = extract_and_store_links()
    print(f"\n  解析到 {total} 条链接，其中 {new} 条为新增入库\n")


def run_stage_3():
    print()
    print("  " + "=" * 60)
    print("  阶段 3：爬取游戏详情页")
    print("  " + "=" * 60)
    crawl_all_detail_pages()
    print()


def run_stage_4():
    print()
    print("  " + "=" * 60)
    print("  阶段 4：查询移动端下载量（tapsearch）")
    print("  " + "=" * 60)
    query_all_mobile_downloads()
    print()


def run_stage_5():
    print()
    print("  " + "=" * 60)
    print("  阶段 5：导出 Excel")
    print("  " + "=" * 60)
    path = export_excel()
    if path:
        print(f"\n  Excel 已导出到：{path}\n")


def run_stage_6():
    print()
    print("  " + "=" * 60)
    print("  阶段 6：生成可视化网页")
    print("  " + "=" * 60)
    export_html()
    print()


def run_full_pipeline():
    run_stage_1()
    run_stage_2()
    run_stage_3()
    run_stage_4()
    run_stage_5()
    run_stage_6()
    show_db_status()
    print("  全流程执行完毕！\n")


# ============================================================
# 交互式主循环
# ============================================================

def interactive_loop():
    current_view_page = 1

    while True:
        clear_screen()
        print_full_screen()

        choice = input("  请输入选项 > ").strip().upper()

        if choice == "1":
            run_stage_1()
        elif choice == "2":
            run_stage_2()
        elif choice == "3":
            run_stage_3()
        elif choice == "4":
            run_stage_4()
        elif choice == "5":
            run_stage_5()
        elif choice == "6":
            run_stage_6()
        elif choice == "7":
            run_full_pipeline()
        elif choice == "Q":
            print("\n  再见！\n")
            break
        elif choice.startswith("V"):
            parts = choice.split()
            if len(parts) > 1 and parts[1].isdigit():
                current_view_page = int(parts[1])
            view_database(page=current_view_page)
        else:
            print("\n  无效选项，请重新输入。")

        if choice != "Q":
            input("\n  按 Enter 返回菜单...")


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="TapTap PC 游戏全量爬虫 (数据库版)")
    parser.add_argument(
        "--auto", action="store_true",
        help="非交互模式，自动运行全流程",
    )
    parser.add_argument(
        "--stage", type=int, choices=[1, 2, 3, 4, 5, 6],
        help="仅运行指定阶段",
    )
    args = parser.parse_args()

    stage_funcs = {
        1: run_stage_1, 2: run_stage_2, 3: run_stage_3,
        4: run_stage_4, 5: run_stage_5, 6: run_stage_6,
    }

    if args.stage:
        stage_funcs[args.stage]()
    elif args.auto:
        run_full_pipeline()
    else:
        interactive_loop()


if __name__ == "__main__":
    main()
