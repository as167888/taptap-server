# TapTap 游戏数据查询

Web 服务，输入游戏名称即可查询 TapTap 平台 PC 端完整数据：总下载量、移动端/PC端分布、评分、发布日期等。

**在线地址**: https://taptap-server-production.up.railway.app

## 功能

- 搜索 TapTap 游戏，返回完整 PC 端数据
- 展示总下载量（全平台）、移动端下载量、PC 端下载量
- 展示评分、评价数量、发布日期
- 深色主题响应式界面

## 技术栈

- Python 3（http.server）
- TapTap protobuf API 签名与解析
- BeautifulSoup4（PC 详情页 JSON-LD 爬取）
- Railway 部署

## 本地运行

```bash
pip install -r requirements.txt
python server/tapserver.py
# 打开 http://localhost:8888
```

## 数据结构

| 字段 | 说明 |
|------|------|
| game_name | 游戏名称 |
| app_id | TapTap App ID |
| total_downloads | 总下载量（全平台） |
| mobile_downloads | 移动端下载量 |
| pc_downloads | PC 端下载量 |
| rating_score | 评分 |
| rating_count | 评价数量 |
| publish_date | 发布日期 |

## API

```
GET /api/pc-detail?q=原神
```

返回 JSON 格式的游戏数据。

---

© 2026 雪球@月旨_投资笔记 | 仅供学习研究
