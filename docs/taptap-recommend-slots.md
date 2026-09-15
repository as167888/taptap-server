# TapTap 安卓客户端 2.96.10 推荐点位全梳理

> 来源: jadx 反编译 (jadx_out_29610) + dex 字符串提取 (apk_extract/strings) + 接口实测 (2026-09)
> 判别广告卡: `type:"ad"` + `ad_info`(via/ad_sign_type/card_style)；模型层预留 `is_ad` 字段

## 一、首页「推荐」信息流（for-you）——核心广告位，已实测

| 项目 | 内容 |
|---|---|
| 接口 | `/feed/v7/list-with-guest?type=recommend`（游客）、`/feed/v7/list-with-user?type=recommend`（登录） |
| 翻页 | `from/limit/session_id`，next_page 相对路径 |
| 兴趣标签 | `/feed/v7/terms-with-guest` / `terms-with-user` |
| 构成 | moment 帖子卡 + `type:"ad"` 广告卡（游客态无自然游戏卡；登录态含个性化游戏卡） |
| 广告密度 | 游客态固定 10%：每会话 60 条在第 3/13/23/33/43/53 条插广告（960 条实测，填充率≈99%） |
| 广告卡结构 | `identification:"ad:<id>"`，`ad_info{title, via="编辑推荐", ad_sign_type=0, card_style=1/2/3, app_summary, image/icon, rating, uri}` |
| 渲染 | `/home_ad/view/service`(AdViewServiceImpl) 按 `card_style` 选 CommunityAdCardViewA/B/C |
| 模型 | TimeLineV7Bean{`is_ad`, `ad_info`, `ad_ttl`, type, app/moment/event...}——`is_ad` 为登录态混排预留 |
| 不感兴趣 | `/dislike/v1/create-with-user`，广告卡带 `position=forum_elite` |
| 实测广告池 | 杖剑传说、我要当老祖、塔塔冒险队、龙魂旅人（主力轮播）+ 率土之滨、三国：谋定天下、我的花园世界、夜幕之下、万龙觉醒、万国觉醒、遗弃之地 |

关注流: `/feed/v7/list-with-user?type=follow&sub_type=all|follow_from_app|follow_from_user`。

## 二、首页其他标签页

| 点位 | 接口/路由 | 广告能力 |
|---|---|---|
| 发现/找游戏 | `/discover-categories/v1/list`、`v1/feed-terms`、`v2/feed-list`；路由 `/main/home/discover` | 合集条目模型 CollectionApp 含 `is_ad`+`identification`（可混广告/运营位） |
| 榜单 | `/app-top/v1/ranking-aggregate`、`app-top/v1/hot-topic`、`hot-topic/v1/awards-by-group`、`editor-choice`；路由 `/main/home/ranking`、`hot-ranking` | 无广告字段，自然排序 + 编辑选择奖项 |
| PC 榜单页 | `/webapiv2/pc-game/v1/list`(web 实测无广告字段)、`/pcgame/v2/banner`(页内 banner 运营位) | banner 位为运营卡 |
| 今日推荐/日历 | `/calendar/v2/recommend-list`、`v2/event-list`、`v2/terms`、`v1/upcoming`、`v1/weekly-review`、`v1/top-events`；position=`today_game_recommend` | 编辑/运营推荐，非竞价广告 |
| 马上玩/即玩 | `/playnow/v1/recommends`、`v1/cards`、`v2/home`、`v2/recommend-items`、`v3/home`、`v3/recommend-items`、`v3/recent-games`、`v3/tab-list`、`v2/game-list`、`v2/favorite-list` | 推荐列表由服务端下发 |
| 云游戏大厅 | `/cloud-game/v1/list`、`v1/pc-app-list` | 可玩列表 |

## 三、游戏详情页

| 点位 | 接口 | 说明 |
|---|---|---|
| 游戏动态 | `/feed/v2|v6/by-app` | 该游戏的社区帖子流 |
| 优质评测推荐 | `/review/v2/recommend-by-app` | 编辑精选评测 |
| 同厂商游戏 | `/app-search/v1/by-developer` | 厂商其他作品 |
| 厂商推荐位 | `/developer/v1/recommend-apps` | 厂商运营推荐 |
| 运营素材 | selling_info(卖点标语)、highlight tags、活动卡 | 编辑运营位 |

## 四、试玩/沙盒（云试玩）

| 点位 | 内容 |
|---|---|
| 广告卡接口 | `/sandbox/v1/ad?app_id&type` → SandBoxAdResponse{`ad_style`, `type`:icon/list/event/video, `label`(角标文字), app, video, list} |
| 试玩加载流 | `/feed/v7/for-sandbox-loading` |
| 游戏内广告位开关 | `show_quit_ad`(退出广告)、`show_installer_ad`、`show_gaming_sidebar_ad`、`show_queuing_ad`、`queuing_ad_dwell_time` |

## 五、社区场景

| 点位 | 接口 |
|---|---|
| 小组推荐 | `/group/v1/recommend`、`recommend-by-me`、`recommend-for-moment` |
| 小组帖子流 | `/feed/v6|v7/by-group`（web 实测 group_id=1 纯帖子无广告） |
| 话题 | `/hashtag/v2/hot-hashtags`、`/hot-topic/v1/community-discussions` |
| 直播 | live_rec 场景（直播推荐卡） |
| 种草/安利 | amway 模块（route `/review_list` → amway/review/page） |
| 抢先测试 | `/app-test/v1/recruit` 系列 |

## 六、搜索

| 点位 | 内容 |
|---|---|
| 聚合搜索 | mixsearch (protobuf: clientapi/mixsearch) |
| 猜你想搜 | search_guess 场景 token |
| 论坛/小组搜索 | `/forum-feed-search/v1/by-keyword`、`/group-search/v2/by-keyword` |

## 七、系统级触达

| 点位 | 内容 |
|---|---|
| 桌面小组件 | `/app-widget/v1/list|detail|check-in-info`（游戏/日历小组件内容下发） |
| 运营弹窗 | `/important-activity-guide/v1/popup`、`/console-game/v2/popup` |
| 启动闪屏 | `taptap_start_splash`（品牌/运营闪屏，非第三方广告） |
| 推送 | pub.taptapdada.com 推送通道（内容服务端决定） |
| 其他 rec 端点 | `/app-moment/v1/rec`、`/app-top/v1/rec`、`/console-game/v2/rec` |

## 八、广告 SDK 原生位（非 feed 混排）

- 已集成: TapAd(`com.tapsdk.tapad` 聚合)、穿山甲(`com.bytedance.sdk.openadsdk`)、荣耀(`com.hihonor.ads`)、`com.byazt.ad`、GDT 痕迹
- 场景: `adn_reward`(激励视频)、`adn_float_menu_interstitial`(浮窗插屏) 等，主要在即玩/小游戏(`instantgame.capability.ad.adn`)内
- 特点: 独立广告请求(如 `/tapad/internal/`)，不进 feed JSON，SDK 强制带"AD"标识

## 广告标志速查

| 点位 | 判别字段 | 实测状态 |
|---|---|---|
| 首页推荐流 | `type:"ad"` + `ad_info.via/ad_sign_type/card_style` | ✅ 10% 固定排期 |
| 发现合集 | `CollectionApp.is_ad` | 模型确认 |
| 试玩广告卡 | `/sandbox/v1/ad` 的 `label` | 模型确认 |
| 信息流模型预留 | `TimeLineV7Bean.is_ad` | 未见线上使用 |
| 榜单/PC 榜 | 无广告字段（自然排序） | ✅ 实测无 |
