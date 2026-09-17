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

## 九、App 真实首页信息流（landing/v9/timeline）——真机抓包确认

> 2026-09-15 真机抓包 x2 (captures_from_desktop/landing_v9_timeline_2026{0915,0915_guest}.json)
> **注意**: App 首页真实接口是 landing/v9/timeline，不是 feed/v7；未登录也可访问
> （Authorization MAC + X-DT 是装机时注册的设备凭证，JWT iss=oauth2:Device）

| 项目 | 内容 |
|---|---|
| 接口 | `GET https://api.taptapdada.com/landing/v9/timeline?action=refresh&allowed_types=satisfaction` |
| 鉴权 | `Authorization: MAC`(设备级签名) + `X-DT`(设备 JWT) + `X-TAP-OAID`(广告标识符) + `X-SMFP`(设备指纹)——定向按设备(OAID/指纹)，不依赖账号登录 |
| 构成 | `type:"app"` 游戏卡(约 9 成) + moment 帖子；翻页 from/limit/session_id |
| **广告标志** | 条目级 `"is_ad": true` + `ad_info{contents, material_id}` —— 与反编译模型 TimeLineV7Bean 完全对应 |
| 广告角标 | `rec_info` 中 `type:"ad"/style:"orange_ad"`；普通卡是 general/hot/ranking/editors_choice |
| 广告素材 | banner 走 `qn-static-tap.tapimg.com`(广告素材 CDN)；广告视频签名 `sign=tapad-xxx`；素材会轮换(同游戏不同 material_id) |
| 竞价痕迹 | `event_log.via` 含 `flow_cpm`(同一次刷新内三条广告 CPM 相同，不同刷新间变化 16.46→11.35)、`trackid`、`uuid`；`log_extra.isid` 前缀 1=自然 / 2=广告 / 4=pcebid 商业渠道 |
| **槽位规律** | 两次抓包完全一致: is_ad 固定在第 1/4/8 条(30%)，pcebid 未标注商业卡固定在第 9 条(10%) |
| 未标注商业 | 无 is_ad 但 `source=pcebid`+`commercial_channel_v2=pce`+flow_cpm(样本: 无限升级 241449、解压箭头 819270)——按普通推荐样式渲染，需持续观察 |

与 feed/v7 社区流的关系：
- **landing/v9/timeline** = App 首页"推荐"真实数据源（游戏卡为主，竞价广告 is_ad:true，槽位 1/4/8）
- **feed/v7/list-with-guest** = 社区内容流(帖子为主，网页端同源)，其 `type:"ad"` 独立卡(via=编辑推荐、固定 10%)是**另一套自营编辑推荐位**
- 两个接口、两套广告体系并存；杖剑传说同时投两套

翻页样本补充 (2026-09-15 23:01, from=10)：
- 首屏槽位固定(1/4/8+9)；**翻页后位置不再固定**，但密度相近：该页 3 条 is_ad + 1 条 pcebid + 1 条帖子广告 = **50% 商业内容**
- **帖子广告形态**：moment 卡《镇邪人》无 is_ad 标志，但 log_extra.isid=2、flow_cpm=46.66 与同批三条广告一致且 uuid 相同——确认是同一竞价批次的付费种草帖，按玩家帖子样式渲染
- **批次 CPM**：同一次刷新的所有广告 flow_cpm 相同（三次采样 11.35 / 16.46 / 46.66 各不同），批量定价/统一底价特征明显
- 新增 item 类型：`type:"satisfaction"` 调查卡（对应请求参数 allowed_types=satisfaction）
- 广告主扩容：斗罗大陆：魂师对决、武林外传：十年之约、梦回甄嬛传（游客池老成员也来竞价）

## 十、模拟持续下滑实测（landing/v9/timeline 无鉴权分页，160 条/2 会话×8 页）

> 2026-09-15 23:11~23:19，工具 landing_scroll_probe.py，页面存档 captures/landing_scroll/
> 结论：landing/v9 可不带 MAC 鉴权分页访问（api 域名 + X-UA 设备 UID）；www 域名同路径被 WAF 拦截

**总量**：160 条 = 自然 109 + is_ad 广告 35 (22%) + 未标注帖子广告 16 (10%)，本轮无 pcebid。

**深度衰减曲线（两个会话完全一致）**：
- 首屏（from=0）：固定商业模板 **第 1/2/4/5/8/9 位共 6 个商业位（60%）**，两次会话位置完全相同
- 第 2~3 屏：50% 密度（AD 3 + 帖AD 2）
- 第 4 屏起衰减：30% → 稳定在 **每页 2 条 is_ad，位置固定第 3、8 位（20%）**
- 会话末页最稀（1 条）
- **新会话重新开始高密度**（第二会话 from=0 又是 60%）——广告密度随会话内深度衰减，刷新/重进恢复

**帖子广告是主力形态之一**：无鉴权画像下首屏 4 条帖子广告（镇邪人 6 次曝光）；isid=2、flow_cpm 同批次，无任何对外标志。

**批次 CPM**：同页广告同价，页间剧烈波动（2.87 ~ 131.90），高价批次多发首屏。个别页出现多批次混合（3 种 CPM 共存一页）。

**广告主频次（160 条内）**：武林外传：十年之约 8 次 > 镇邪人 6 > 杖剑传说 4 = 长安幻想 4 > 永夜起源 3 > 传奇岁月/指尖魔兽/一念逍遥 2 > 其余 1 次（梦幻西游再续前缘、星际猎人、大话西游归来、斗罗大陆传承）。

## 广告标志速查

| 点位 | 判别字段 | 实测状态 |
|---|---|---|
| 登录态首页 landing/v9 | 条目 `"is_ad": true` + `ad_info.material_id` + `rec_info type=ad` | ✅ 槽位固定 1/4/8 (30%)，未登录同样生效 |
| 首页游客推荐流 | `type:"ad"` + `ad_info.via/ad_sign_type/card_style` | ✅ 10% 固定排期 |
| 发现合集 | `CollectionApp.is_ad` | 模型确认 |
| 试玩广告卡 | `/sandbox/v1/ad` 的 `label` | 模型确认 |
| 信息流模型预留 | `TimeLineV7Bean.is_ad` | ✅ 登录态线上使用中(见九) |
| 榜单/PC 榜 | 无广告字段（自然排序） | ✅ 实测无 |
| 商业渠道未标注 | `source=pcebid`+`flow_cpm` 但无 is_ad | ⚠ 样本 1 例，观察中 |
