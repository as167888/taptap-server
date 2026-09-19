# TapTap API 深度挖掘报告（2.96.10 APK 解包）

> 从 7 个 dex 中提取 **489 个带版本号端点**（总候选路径 894 个），实测验证后可用的信息型端点如下。
> 全部为**无鉴权可访问**（仅需 X-UA 设备身份），测试日期 2026-09-17。

## 一、⭐ 头号发现：批量游戏统计接口

```
GET https://api.taptapdada.com/app/v1/multi-get-full-platform?ids=<逗号分隔ID>
```

| 项目 | 实测结果 |
|---|---|
| 单次上限 | **100 个 id**（105+ 返回空列表） |
| 速度 | 100 个 id → **0.68 秒**、416 KB |
| 鉴权 | 无需 MAC 签名 |
| 请求格式 | ids 的逗号**不能 URL 编码**，否则 400 |

### 返回的 stat 统计对象（以《杖剑传说》为例）

```json
{
  "hits_total": 3555729,           // 移动端累计下载/浏览量 ← 等于网页详情页的下载量
  "pc_download_count": 0,          // PC 端下载量
  "pc_sale_count": 0,              // PC 端销量
  "review_count": 41244,           // 评测数
  "fans_count": 2132196,           // 粉丝数
  "reserve_count": 314923,         // 预约数
  "wish_count": 1111,              // 想要数
  "topic_count": 42663,            // 帖子数
  "feed_count": 42663,
  "bought_count": 0, "album_count": 0, "video_count": 0,
  "recent_sandbox_played_count": 0,// 近期试玩数
  "vote_info": {"1":3587,"2":2089,"3":1814,"4":5954,"5":27206},  // 各档评分人数
  "rating": {"score":"8.6","latest_score":"7.8","latest_version_score":"7.4",
             "latest_review_count":141,"latest_version_review_count":37}
}
```

### 🔥 与你现有爬虫的关系（重要）

**`hits_total` = 你数据库的 `mobile_downloads`，`pc_download_count` = `pc_downloads`**——已用你库中 5 款游戏交叉验证，数值只差几百（时间差）：

| 游戏 | API hits_total | 你库 mobile | API pc_download | 你库 pc |
|---|---|---|---|---|
| 异环 | 8,688,080 | 8,685,445 | 1,037,057 | 1,036,613 |
| 鸣潮 | 23,687,844 | 23,685,508 | 262,817 | 262,454 |
| 三角洲行动 | 21,205,259 | 21,201,227 | 401,660 | 400,850 |
| 心动小镇 | 61,089,764 | 61,083,248 | 382,854 | 382,162 |
| 洛克王国：世界 | 6,740,776 | 6,739,733 | 245,649 | 245,466 |

**结论**：你现有爬虫逐个抓 HTML 详情页（`crawl_detail_page`）的方式，**可被此接口完全替代**——3514 款游戏按每批 100 个只需 **36 个请求、约 25 秒**（原方案 3514 个页面请求）。

**工具已就绪**：[bulk_game_stats.py](../bulk_game_stats.py)

```bash
python bulk_game_stats.py                  # 读 crawler/output/taptap_pc.db 全部 app_id
python bulk_game_stats.py --update-db      # 顺便回写数据库 mobile/pc 下载量
python bulk_game_stats.py --ids 717836,2315
# 结果追加写入 game_stats_api.jsonl(含全部统计字段)
```

## 二、其他新增可用端点

| 端点 | 返回内容 | 用途 |
|---|---|---|
| `GET /app-top/v2/hits?app_id=X` | 游戏详情页的**相似推荐列表**（10 条/页，含 `is_ad` 字段、`log_keyword`、`total`、`prev/next_page`） | 可监控详情页的推荐位是否插广告 |
| `GET /apk/v1/list-by-app?app_id=X` | **版本历史**：`version_code`、`version_label`、`update_date`、`whatsnew`（更新日志） | 追踪游戏更新节奏、版本号 |
| `GET /app-news/v1/list?app_id=X` | `announcement_list`(公告) + `activity_list`(活动) | 游戏运营动态 |
| `GET /app-news/v1/tops-by-apps?app_ids=X,Y` | 批量取游戏的**头条公告**（`label_type`、`title`、`content`） | 批量监控运营动作 |
| `GET /app/v1/android-packages?app_id=X` | 渠道包列表：`package_name`（如 `com.m88.zjcs.g`）、`is_channel` | 识别渠道分发 |
| `GET /app-top/v1/hot-topic?app_id=X` | 该游戏的热门话题 | 社区热度 |

## 三、端点全景（489 个带版本号接口 · 按模块）

| 模块 | 数量 | 代表端点 |
|---|---|---|
| moment / moment-comment | 42 | `/moment/v3/*`、`/moment-rec/v2/relate` |
| app / app-* | 26+ | `/app/v1/*`（详情、包、创意工坊） |
| cloud-game | 22 | `/cloud-game/v1~v3/*`（云游戏节点、试玩、VIP） |
| review | 20 | `/review/v2/recommend-by-app` |
| steam | 14 | Steam 账号绑定与数据 |
| user-app | 14 | 用户-游戏关系 |
| account | 12 | 账号资料、绑定 |
| reserve | 12 | 预约 |
| feed | 11 | `/feed/v2~v7/*`（推荐流，含广告） |
| order | 11 | 订单/支付 |
| playnow | 11 | 即玩推荐 |
| calendar | 10 | 今日推荐/游戏日历 |
| group | 10 | 小组推荐与帖子流 |
| notification / message | 15 | 通知与私信 |
| achievement | 8 | 成就 |
| app-test | 8 | 抢先测试招募 |
| favorite / vote / apk | 21 | 收藏、评分、安装包 |
| search | 8 | `/search/v3~v6/*`（v6 为聚合搜索） |
| leaderboard | 3 | 排行榜卡 |
| app-top | 4 | 榜单聚合、热门话题、相似推荐 |
| pc-game | 4 | PC 榜单（你现用） |

完整清单：`_endpoints.txt`（489 行）

## 四、实测 404（需登录/特定参数/客户端版本）

以下端点在无鉴权 + 常规参数下返回 404，需真机抓包补齐参数或带 MAC 签名才能用：

`/landing/v9/refresh-ad`（**广告刷新专用端点，值得用真机抓包验证**）、`/landing/v1/custom-ranking`、
`/app/v1/internal-ratings`、`/app-top/v1/ranking-aggregate`、`/search/v6/agg-search`、
`/hot-topic/v1/editor-choice`、`/hashtag/v2/hot-hashtags`、`/leaderboard/v1/stats-card`、
`/app-tag/v1/by-tag`、`/app/v1/mini-multi-get`

> `/landing/v9/refresh-ad` 是关键线索——首页推荐流的**广告刷新**可能有独立接口，如果抓到它，就能单独研究“广告位如何被刷新/替换”。

## 五、建议

1. **立刻可做**：把下载量抓取从 HTML 爬虫切换到 `multi-get-full-platform`（36 请求 vs 3514 请求），配合 `--update-db` 直接写回你现有数据库；
2. **值得扩展监控**：`/app-top/v2/hits` 带 `is_ad` 字段 → 详情页推荐位也有广告位可监控；
3. **需要你配合**：`/landing/v9/refresh-ad` 用手机抓包（点进首页后下拉刷新几次）验证是否存在、返回什么；
4. 频率建议：接口虽快，仍建议每批间隔 2 秒以上（工具默认 2s），避免 WAF 触发。
