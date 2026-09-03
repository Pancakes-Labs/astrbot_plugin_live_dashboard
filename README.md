<!-- markdownlint-disable MD028 -->
<!-- markdownlint-disable MD033 -->
<!-- markdownlint-disable MD041 -->

![astrbot_plugin_live_dashboard](https://socialify.git.ci/Pancakes-Labs/astrbot_plugin_live_dashboard/image?custom_description=%E9%83%BD%E6%9D%A5%E8%A7%86%E5%A5%B8%E6%88%91%E5%96%B5+%E2%9D%A4%EF%B8%8F&description=1&font=Inter&forks=1&issues=1&language=1&name=1&owner=1&pattern=Signal&pulls=1&stargazers=1&theme=Auto)

<p align="center">
  <img src="assets/PluginRank.svg" alt="Plugin Rank">
  <img src="assets/StarRank.svg" alt="Star Rank">
  <img src="assets/ShitMountain.svg" alt="ShitMountain">
</p>

<img width="250" height="250" align="right" alt="logo" src="https://github.com/user-attachments/assets/eeafbd66-5613-41a6-81c7-78a997c1c330" />

<p align="center">
  <img src="https://img.shields.io/badge/License-AGPL_3.0-blue.svg" alt="License: AGPL-3.0">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/AstrBot-v4.11.2+-orange.svg" alt="AstrBot v4.11.2+">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AstrBot-v4.27.4%20Compatible-brightgreen.svg" alt="Compatible with AstrBot v4.27.4">
  <img src="https://img.shields.io/github/v/release/Pancakes-Labs/astrbot_plugin_live_dashboard?label=Release&color=brightgreen" alt="Latest Release">
  <img src="https://img.shields.io/badge/QQ群-1033089808-12B7F3.svg" alt="QQ群">
</p>

[![Moe Counter](https://count.getloli.com/get/@DBJD-CR5?theme=moebooru)](https://github.com/Pancakes-Labs/astrbot_plugin_live_dashboard)

---

一个为 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 设计的「视奸面板」插件。  
用于对接上游 [Live Dashboard](https://github.com/Monika-Dream/live-dashboard) 服务，支持在私聊/群聊中通过指令快速查询当前手机、电脑的活动状态信息。  
还支持用自然语言让 LLM 自主查询，让 Bot 和群友都能随时随地视奸你！❤️

## 📑 快速导航

- [✨ 功能特性](#-功能特性)
- [📊 输出示例](#-输出示例)
- [🚀 安装与使用](#-安装与使用)
- [📋 指令说明](#-指令说明)
- [🤖 函数工具自动调用](#-函数工具自动调用)
- [📑 插件配置项详解](#-插件配置项详解)
- [📂 插件目录与结构](#-插件目录与结构)
- [🏗️ 架构说明](#️-架构说明)
- [❓ 常见问题](#-常见问题)
- [🚧 已知限制](#-已知限制)
- [📄 许可证](#-许可证)

---
<!-- 开发者的话 -->
> **开发者的话：**
>
> 大家好，我是 DBJD-CR，这是我为 AstrBot 开发的第三个插件，如果存在做的不好的地方还请理解。
>
> 最开始是在 B 站上刷到的项目，觉得挺有意思的就部署了一下。顺便让 AstrBot 强兼了该项目，并满足一下我的“赛博露出癖”（bushi）
>
> 和我写的其他插件一样，本插件也是"Vibe Coding"的产物。
>
> 所以，**本插件的所有文件内容，全部由 AI 编写完成**，我几乎没有为该插件编写任何一行代码，仅进行了架构设计与修改部分文字描述和负责本文档的润色。所以，或许有必要添加下方的声明：

> [!WARNING]  
> 本插件和文档由 AI 生成，内容仅供参考，请仔细甄别。
>
> 插件目前仍处于开发阶段，无法 100% 保证稳定性与可用性。

> 不过，这次的开发过程还是相当顺利的，小半天就把插件搓好了，用着也挺顺手，能力提高了不少喵！
>
> 虽然这个插件功能比较简单，也还是诚邀各路大佬对本插件进行测试和改进，希望大家多多指点。
>
> 如果觉得这个插件比较好玩的话，**就为这个插件点个** 🌟 **Star** 🌟 **吧~** ，这是对我们的最大认可与鼓励！

> [!NOTE]
> 虽然本插件的开发过程中大量使用了 AI 进行辅助，但我保证所有内容都经过了我的严格审查，所有的 AI 生成声明都是形式上的。你可以放心参观本仓库和使用本插件。
>
> 目前插件的主要功能都能正常运转。但仍有很多可以优化的地方。

> [!TIP]
> 本项目的相关开发数据 (持续更新中)：
>
> 开发时长：累计 3 天（主插件部分）
>
> 累计工时：约 23 小时（主插件部分）
>
> Tokens Used：69,464,300

---

## ✨ 功能特性

实时查询设备状态，支持通过 AstrBot 的 WebUI 进行配置，具备完善的黑白名单机制，控制回复内容，避免输出过长或泄露不希望展示的信息。

- 请求上游接口：`GET {base_url}/api/current`
- 聚合展示：
  - 在线设备数
  - 设备名 / 平台 / 在线状态
  - 当前应用名
  - 展示标题（服务端已按隐私分级净化）
  - 电量与充电状态
  - 音乐信息
  - 最后上报时间
  - 最近活动
- 时间线查询：查询指定日期每个应用的使用时长
- 健康数据查询：查询心率/步数/睡眠等
- 服务状态查询：检查上游服务连通性、运行时长与时间
- 好友面板聚合：通过上游只读代理查询好友面板状态
- 读侧 NSFW 兜底过滤：对服务端可能残留的敏感标题在渲染层追加打码

## 📊 输出示例

<details>
<summary>指令 /视奸 输出示例</summary>

```text
📊 Live Dashboard 状态面板
在线设备：1/1
当前访客：1
服务端时间：09-03 15:43:23

• DBJD-CR 的 华硕天选4 i9-13900H RTX4060 [在线] (windows)
  现在：正在QQ上收发消息喵~
  应用：QQ
  标题：（无可展示标题）
  🔋 电量：100% ⚡充电中
  🎵 音乐：暂无播放
  🕒 上报：09-03 15:43:20

最近活动（DBJD-CR 的 华硕天选4 i9-13900H RTX4060）：
  1. 刚刚 正在QQ上收发消息喵~
  2. 43秒前 正在用Cursor疯狂写bug喵~「README.md - astrbot_plugin_live_dashboard - Cursor」
  3. 48秒前 正在用Edge网上冲浪喵~「astrbot_plugin_disaster_warning/README.md at main · Pancakes-Labs/astrbot_plugin_disaster_warning」
  4. 1分钟前 正在用Cursor疯狂写bug喵~「README.md - astrbot_plugin_live_dashboard - Cursor」
  5. 1分钟前 正在用Edge网上冲浪喵~「astrbot_plugin_disaster_warning/README.md at main · Pancakes-Labs/astrbot_plugin_disaster_warning」
  6. 1分钟前 正在用Edge网上冲浪喵~「Pancakes-Labs/astrbot_plugin_disaster_warning: 基于 AstrBot 的新一代灾害预警平台。无缝聚合全球权威数据，实时追踪地震、海啸、气象与台风动态。搭载现代化 WebUI、专业级可视化渲染与…」
  7. 1分钟前 正在用Edge网上冲浪喵~「灾害预警管理端」
  8. 2分钟前 正在QQ上收发消息喵~
  9. 2分钟前 正在用Cursor疯狂写bug喵~「README.md - astrbot_plugin_live_dashboard - Cursor」
  10. 2分钟前 正在QQ上收发消息喵~
  11. 3分钟前 正在QQ上收发消息喵~
  12. 3分钟前 正在QQ上收发消息喵~
  13. 4分钟前 正在用Cursor疯狂写bug喵~「README.md - astrbot_plugin_live_dashboard - Cursor」
  14. 4分钟前 正在QQ上收发消息喵~
  15. 4分钟前 正在用Cursor疯狂写bug喵~「README.md - astrbot_plugin_live_dashboard - Cursor」
  16. 5分钟前 正在用Cursor疯狂写bug喵~「main.py - astrbot_plugin_live_dashboard - Cursor」
  17. 5分钟前 正在用Cursor疯狂写bug喵~「timeline_renderer.py - astrbot_plugin_live_dashboard - Cursor」
  18. 5分钟前 正在QQ上收发消息喵~
  19. 6分钟前 正在QQ上收发消息喵~
  20. 6分钟前 正在用Cursor疯狂写bug喵~「timeline_renderer.py - astrbot_plugin_live_dashboard - Cursor」
```

</details>

<details>
<summary>指令 /视奸时间线 输出示例</summary>

```text
📜 Live Dashboard 时间线（2026-09-03）

各应用累计时长（DBJD-CR 的 华硕天选4 i9-13900H RTX4060）：
  idle：7小时12分钟
  Cursor：3小时1分钟
  哔哩哔哩：1小时12分钟
  Microsoft Edge：31分钟
  QQ：30分钟
  app：15分钟
  JQuake：6分钟
  Photos：6分钟
  终端：1分钟
  文件资源管理器：1分钟
  Steam：1分钟
  GlobalQuake：小于1分钟
  搜索：小于1分钟
  oopz：小于1分钟
  EQuake_release_3.4.4.10c：小于1分钟

时间线片段（DBJD-CR 的 华硕天选4 i9-13900H RTX4060）：
  02:06 正在用Edge网上冲浪喵~「DBJD-CR Now +24」
  02:06 正在用Edge网上冲浪喵~「AstrBot - 仪表盘 +24」
  02:06 正在用Edge网上冲浪喵~
  02:06 正在用Edge网上冲浪喵~「DBJD-CR Now +22」
  02:06 正在用命令行敲命令喵~
  02:06 正在用Edge网上冲浪喵~
  02:06 正在用Edge网上冲浪喵~「localhost +22」
  02:06 正在用Edge网上冲浪喵~「AstrBot - 仪表盘 +22」
  02:06 正在监测全球地震喵~「GlobalQuake 1.0.1」
  02:07~02:07 正在翻文件夹找东西喵~ ×6
  02:07 正在QQ上收发消息喵~
  02:07 正在翻文件夹找东西喵~
  02:07 正在盯紧地震监测喵~「PopupMessageWindow」
  02:08 正在翻文件夹找东西喵~
  02:08 正在Steam喜加一喵~「好友列表」
  02:08 正在Steam喜加一喵~「Steam」
  02:08 正在QQ上收发消息喵~
  02:08~02:09 正在Steam喜加一喵~「Steam」 ×2（1分钟）
  02:10 正在翻文件夹找东西喵~
  02:10 正在Steam喜加一喵~「Steam」
  02:10 正在QQ上收发消息喵~
  02:10~02:15 正在翻相册喵~「kmc_20230807_125212.jpg」 ×6（6分钟）
  02:16~04:53 暂时离开了喵~「User is away」 ×158（2小时38分钟）
  04:54 正在盯紧地震监测喵~「JQuake」
  04:54~04:58 正在忙别的喵~「要石 kanameishi v2.8.0」 ×5（5分钟）
  04:59~06:49 暂时离开了喵~「User is away」 ×111（1小时51分钟）
  06:50~06:54 正在忙别的喵~「要石 kanameishi v2.8.0」 ×5（5分钟）
  06:55~07:21 暂时离开了喵~「User is away」 ×27（27分钟）
  07:22~07:26 正在忙别的喵~「要石 kanameishi v2.8.0」 ×5（5分钟）
  07:27~07:44 暂时离开了喵~「User is away」 ×18（17分钟）
  07:44~07:48 正在盯紧地震监测喵~「JQuake」 ×5（5分钟）
  07:49~09:36 暂时离开了喵~「User is away」 ×108（1小时48分钟）
  09:37 正在QQ上收发消息喵~
  09:37~09:38 正在用Edge网上冲浪喵~「AstrBot - 仪表盘 +22」 ×2（2分钟）
  09:39 正在QQ上收发消息喵~
  09:39 正在用Edge网上冲浪喵~
  09:39 正在QQ上收发消息喵~
  09:39 正在用Edge网上冲浪喵~
  09:39 正在用Edge网上冲浪喵~「开发者审核 - FAN Studio +22」
  09:39 正在用Edge网上冲浪喵~「灾害预警 - AstrBot Cloud +22」
  09:39~09:40 正在用Edge网上冲浪喵~「DBJD-CR (大饼鸡蛋) +22」 ×2（1分钟）
  09:41 正在用Edge网上冲浪喵~「DBJD-CR (大饼鸡蛋) / August 2026 +22」
  09:41 正在用Edge网上冲浪喵~「DBJD-CR (大饼鸡蛋) / July 2026 +22」（1分钟）
  09:41 正在用Edge网上冲浪喵~「Pancakes-Labs/astrbot_plugin_count_loc: 一个为 AstrBot 设计的公开代码仓库行数统计分析插件。 可对任意公开的 GitHub 或 GitLab 仓库的代码指标进行快捷获取和分析。 A stat…」（1分钟）
  09:42 正在用Edge网上冲浪喵~「Pull requests · Pancakes-Labs/astrbot_plugin_proactive_chat +22」
  09:42 正在用Edge网上冲浪喵~「AstrBot - 仪表盘 +22」
  09:42 正在QQ上收发消息喵~
  09:43 正在用Edge网上冲浪喵~「AstrBot - 仪表盘 +22」
  09:43 正在QQ上收发消息喵~
  09:43 正在用Edge网上冲浪喵~「AstrBot - 仪表盘 +22」
  … 还有更多片段未展示（上限 50 条）
```

</details>

## 🚀 安装与使用

1. **下载插件**: 通过 AstrBot 的插件市场下载。或从本 GitHub 仓库的 Release 下载 `astrbot_plugin_live_dashboard` 的 `.zip` 文件，在 AstrBot WebUI 中的插件页面中选择 `从文件安装` 。
2. **安装依赖**: 本插件的核心依赖为 `httpx`，插件下载安装时会自动安装插件所需的依赖，通常无需额外安装。如果你的环境中确实缺少相关依赖，请安装：

   ```bash
   pip install httpx
   ```

3. **重启 AstrBot (可选)**: 如果插件没有正常加载或生效，可以尝试重启你的 AstrBot 程序。
4. **配置插件**: 进入 AstrBot WebUI，找到 `视奸面板` 插件，选择 `插件配置` 选项，配置相关参数：

- `Live Dashboard 服务地址`（例如 `https://your-domain.com` `http://localhost:3000` `http://127.0.0.1:3000`）

若你的服务端或反向代理要求鉴权，再填写：

- `可选鉴权 Token`

> [!WARNING]  
> 本插件是否能正常运行完全依赖你是否配置了相关服务，如果未配置相关 URL 并启动 Live Dashboard 服务，插件功能将无法正常使用。
>
> 有关 Live Dashboard 的部署和本地数据上报，请参考上游项目的 [README文档](https://github.com/Monika-Dream/live-dashboard) 进行部署。

---

## 📋 指令说明

| 指令 | 别名 | 说明 |
| :-- | :-- | :-- |
| `/视奸` | `/ldb` `/livedashboard` `/设备状态` `/状态面板` | 查询当前 Live Dashboard 状态 |
| `/视奸时间线` | `/视奸历史` | 查询指定日期（缺省今天）各应用使用时长 |
| `/视奸健康` | `/健康数据` | 查询指定日期（缺省今天）心率/步数/睡眠等健康数据 |
| `/视奸服务状态` | | 检查上游服务连通性、运行时长与时间 |
| `/视奸好友` | `/好友面板` | 列出好友面板或按名称查询好友状态 |

### 命令示例

<details>
<summary>点击查看命令示例</summary>

```bash
# 此处列出了插件内指令参数较为复杂的指令，您可按需查找使用。
#
# ============================================================
# 1. 时间线查询
# ============================================================

# --- 应用使用时间线 ---
# 格式：/视奸时间线 [日期]
# 日期格式：YYYY-MM-DD；缺省为今天；格式非法会返回明确提示
# 1. 查询今天各应用的使用时长
/视奸时间线
# 2. 查询指定日期
/视奸时间线 2026-09-03
# 3. 别名示例
/视奸历史 2026-09-03

# ============================================================
# 2. 健康数据查询
# ============================================================

# --- 健康数据 ---
# 格式：/视奸健康 [日期]
# 日期格式：YYYY-MM-DD；缺省为今天
# 1. 查询今天的心率/步数/睡眠等身体指标
/视奸健康
# 2. 查询指定日期
/视奸健康 2026-09-03
# 3. 别名示例
/健康数据 2026-09-03

# ============================================================
# 3. 好友面板查询（多面板聚合）
# ============================================================

# --- 好友面板 ---
# 格式：/视奸好友 [名称] [子命令] [日期]
# 子命令：状态（默认）/ 时间线 / 健康 / 配置（支持中英文关键词）
# 面板匹配：名称或 id 不区分大小写的子串匹配
# 1. 无参数：列出所有已配置的好友面板
/视奸好友
# 2. 查询某好友面板的实时状态（默认子命令）
/视奸好友 小明
# 3. 查询某好友面板指定日期的时间线（缺省今天）
/视奸好友 小明 时间线
/视奸好友 小明 时间线 2026-09-03
# 4. 查询某好友面板指定日期的健康数据（缺省今天）
/视奸好友 小明 健康
/视奸好友 小明 健康 2026-09-03
# 5. 查询某好友面板的站点配置信息（标题/描述，基于只读代理）
/视奸好友 小明 配置
# 6. 别名 + 英文子命令示例（按 id 匹配）
/好友面板 xiaoming timeline 2026-09-03
/好友面板 xiaoming health
/好友面板 xiaoming config
```

</details>

---

## 🤖 函数工具自动调用

插件内置了 4 个 LLM 函数工具，支持 Bot 通过自然语言对话"自行调用插件的查询能力"，覆盖实时状态、时间线、健康数据与好友面板四大能力。

| 工具名 | 能力 | 参数 |
| :-- | :-- | :-- |
| `query_live_dashboard_status` | 查询当前实时设备状态 | 无 |
| `query_live_dashboard_timeline` | 查询指定日期的应用使用时间线 | `date`（可选，`YYYY-MM-DD`，缺省今天） |
| `query_live_dashboard_health` | 查询指定日期的健康数据 | `date`（可选，`YYYY-MM-DD`，缺省今天） |
| `query_friend_dashboard_status` | 查询指定好友面板的实时状态 | `name`（必填，面板名称或 id） |

- 注册方式：`@filter.llm_tool` 注册工具本体。
- 触发引导：通过 `@filter.on_llm_request` 在每次 LLM 请求前向 `system_prompt` 注入工具使用规范，提示模型在涉及"实时设备状态 / 现在在做什么 / 视奸状态 / 时间线 / 健康数据 / 好友面板"等意图时优先调用对应工具。

效果示例：

<img width="608" height="610" alt="LLMTool" src="https://github.com/user-attachments/assets/c9857a65-c6bb-416e-b46d-e174355caedc" />
<img width="940" height="510" alt="LLMTools" src="https://github.com/user-attachments/assets/56fbdefe-c45f-4cd5-b21b-b4085ee522de" />

### 工具调用行为

1. **先校验、再分发**：工具在调用前依次进行功能开关校验（时间线 / 健康 / 好友工具受对应开关约束，状态工具不受开关限制）与黑白名单拦截（群/用户黑名单），被禁用或命中时返回明确提示，不会发起无效请求。
2. **自动复用主查询链路**：工具与对应命令共用同一套服务层编排、上游请求与渲染逻辑。
3. **结果可直接给 LLM 观察**：工具返回"成功/失败"文本，成功时附带原样面板文本；失败时返回可解释的错误原因（未配置地址、日期格式错误、超时、鉴权失败、网络错误等）。
4. **支持自然连续对话**：LLM 拿到工具结果后可继续按人设组织自然回答，不需要用户再次触发命令。

### 使用建议

- 若你希望 Bot 更积极地在对话中调用这些工具，请确保当前会话开启了函数调用能力。
- 当 Bot 回答里出现"查询失败"时，优先检查 `Live Dashboard 服务地址`、`可选鉴权 Token`、网络连通性与上游服务运行状态；若提示"已禁用"，请检查对应命令功能开关配置。

---

## 📑 插件配置项详解

本插件在 AstrBot WebUI 中提供了完备且结构清晰的配置体系，采用分层级、模块化的设计。
您可以在 AstrBot 管理面板中根据隐私保护需求、设备分布与查询场景进行精细化定制。

<details>
<summary>点击查看配置项详解</summary>

### 🌐 1. 连接配置 (`connection`)

配置与上游 Live Dashboard 服务的网络通信参数，包括服务端地址、鉴权凭据与超时控制。

- **Live Dashboard 服务地址 (`base_url`)**:
  - 类型：`String`
  - 默认值：`""`
  - 说明：Live Dashboard 部署的基础 URL 地址（必填项）。
  - 提示：
    - 支持填写例如 `https://your-domain.com` 或 `http://localhost:3000`、`http://127.0.0.1:3000`。
    - **不需要**在末尾附带 `/api/current` 等具体接口路径，插件会自动完成各子路由的规范化拼接。

- **可选鉴权 Token (`auth_token`)**:
  - 类型：`String`
  - 默认值：`""`
  - 说明：访问上游服务或反向代理网关所需的身份验证凭证。
  - 提示：
    - 若上游服务或 Nginx/Caddy 等反向代理启用了 Bearer 鉴权，在此处填入 Token 字符串。
    - 插件发起 HTTP 请求时会自动将其封装为 `Authorization: Bearer <auth_token>` 请求头。若服务端未启用鉴权，请保持留空。

- **请求超时时间（秒） (`request_timeout_sec`)**:
  - 类型：`Integer`
  - 默认值：`30`
  - 范围：`5 - 600`（步长 `5`）
  - 说明：与上游服务建立连接及接收响应数据的超时阈值。
  - 提示：在跨国网络或弱网环境下部署时，可适当调大至 `60` 秒以上以避免网络波动引发的超时中断。

```json
{
  "connection": {
    "base_url": "https://dashboard.example.com", // Live Dashboard 基础服务地址
    "auth_token": "",                           // 可选鉴权 Bearer Token（未启用请留空）
    "request_timeout_sec": 30                   // HTTP 请求超时时间（秒）
  }
}
```

---

### 📟 2. 输出范围配置 (`output_scope`)

控制哪些设备进入查询与渲染流水线，支持在线状态过滤、数量截断以及基于设备名称的黑白名单筛选。

- **是否包含离线设备 (`include_offline_devices`)**:
  - 类型：`Boolean`
  - 默认值：`false`
  - 说明：控制是否在状态面板中输出离线状态（`is_online=false`）的设备。
  - 提示：开启后可查看离线设备的最后上报记录；关闭后仅输出当前活跃在线的设备。

- **最多展示设备数量 (`max_devices`)**:
  - 类型：`Integer`
  - 默认值：`10`
  - 说明：状态面板单次渲染的最大设备数量上限。
  - 提示：用于防止拥有多台设备的用户在群聊中触发过长消息，超过此上限的设备将被自动截断。

- **设备白名单关键词 (`device_whitelist_keywords`)**:
  - 类型：`String`
  - 默认值：`""`
  - 说明：仅展示设备名称（`device_name`）命中白名单关键词的设备。
  - 提示：
    - 多项支持使用**逗号**（`,`/`，`）、**分号**（`;`/`；`）或**换行符**进行分隔。
    - 匹配规则为不区分大小写的子串包含匹配。
    - 留空表示不限制白名单。

- **设备黑名单关键词 (`device_blacklist_keywords`)**:
  - 类型：`String`
  - 默认值：`""`
  - 说明：设备名称（`device_name`）命中黑名单关键词的设备将被直接剔除并不予展示。
  - 提示：
    - 多项支持使用逗号、分号或换行符分隔。
    - **优先级高于白名单**（当同一设备同时命中黑白名单时，黑名单优先隐藏）。

```json
{
  "output_scope": {
    "include_offline_devices": false,         // 是否输出离线设备
    "max_devices": 10,                        // 面板单次最多展示设备数量
    "device_whitelist_keywords": "",          // 设备名白名单（留空不限）
    "device_blacklist_keywords": "Test,OldPC" // 设备名黑名单（命中则隐藏）
  }
}
```

---

### 🛡️ 3. 访问控制与隐私安全 (`access_control`)

针对消息来源会话、特定用户以及敏感输出内容实施细粒度的访问拦截与脱敏替换，构筑隐私防线。

- **群组黑名单 (`group_blacklist_sessions`)**:
  - 类型：`String`
  - 默认值：`""`
  - 说明：配置被禁止使用视奸查询功能的群组会话列表。
  - 提示：
    - 支持填写完整的 `session_id`（例如 `GroupMessage:123456789`）。
    - 亦支持仅填写尾部纯群号（例如 `123456789`），插件将自动按 `:{群号}` 后缀执行安全匹配。
    - 多项支持逗号、分号或换行分隔。命中黑名单的群会话将直接静默拒绝或忽略响应。

- **用户黑名单 (`user_blacklist_senders`)**:
  - 类型：`String`
  - 默认值：`""`
  - 说明：配置被禁止使用视奸查询功能的用户发送者 ID 列表。
  - 提示：
    - 请填写发送者的完整 ID（例如 QQ 号 `987654321`）。
    - 多项支持逗号、分号或换行分隔。命中黑名单的用户发起查询时将被直接拒绝。

- **信息黑名单关键词 (`info_blacklist_keywords`)**:
  - 类型：`String`
  - 默认值：`""`
  - 说明：针对活动叙事（`现在`）、应用名称（`应用`）与窗口标题（`标题`）的敏感内容脱敏关键词库。
  - 提示：
    - 多项支持逗号、分号或换行分隔。
    - 匹配不区分大小写。可填入真实姓名、私密应用、特定项目名或敏感窗口特征词。

- **信息黑名单替换文案 (`info_blacklist_replacement`)**:
  - 类型：`String`
  - 默认值：`"不想让你看到我在干什么喵~"`
  - 说明：当活动叙事、应用名或窗口标题命中上述关键词时，用于替换真实内容的占位文案。

```json
{
  "access_control": {
    "group_blacklist_sessions": "123456789; 987654321", // 禁止查询的群号/会话
    "user_blacklist_senders": "111222333",              // 禁止查询的用户 ID
    "info_blacklist_keywords": "私密, 密码, SecretApp",  // 敏感词拦截库
    "info_blacklist_replacement": "不想让你看到我在干什么喵~" // 命中脱敏后的替换文案
  }
}
```

---

### 🧩 4. 输出字段开关 (`output_fields`)

控制实时状态面板中各个数据维度的显隐状态，帮助用户在信息丰富度与个人隐私之间取得完美平衡。

- **显示设备平台 (`show_platform`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：是否在设备头部展示操作系统平台标识（如 `windows`、`macos`、`android`、`linux` 等）。

- **显示当前应用名 (`show_app_name`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：是否展示当前前台运行的具体应用程序名称（如 `QQ`、`Cursor`、`Microsoft Edge` 等）。

- **显示窗口净化标题字段 (`show_display_title`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：是否展示服务端按隐私等级净化后的窗口/标签页标题。
  - 提示：若希望进一步提升个人隐私等级，可关闭此开关以隐藏所有具体标题。

- **显示电量信息 (`show_battery`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：是否展示设备的电池剩余百分比与充放电状态（`⚡充电中` 等，仅针对在线设备）。

- **显示音乐信息 (`show_music`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：是否展示设备当前正在播放的媒体/音乐曲目及艺术家信息（仅针对在线设备）。

- **显示最后上报时间 (`show_last_seen`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：是否展示设备最近一次向上游服务同步心跳与活动状态的时间戳。

- **显示访客数量 (`show_viewer_count`)**:
  - 类型：`Boolean`
  - 默认值：`false`
  - 说明：是否在面板顶部展示当前正在浏览 Live Dashboard Web 前端的实时访客数。

- **显示服务端时间 (`show_server_time`)**:
  - 类型：`Boolean`
  - 默认值：`false`
  - 说明：是否在面板顶部展示上游 Live Dashboard 服务端的当前系统时间。

- **显示最近活动列表 (`show_recent_activities`)**:
  - 类型：`Boolean`
  - 默认值：`false`
  - 说明：是否在每个设备下方附加展示其近期的历史活动轨迹时间线片段。

- **最近活动状态最多展示条数 (`recent_activities_max`)**:
  - 类型：`Integer`
  - 默认值：`5`
  - 范围：`1 - 20`（步长 `1`）
  - 说明：仅在开启 `show_recent_activities` 时生效，控制单台设备最多输出的历史活动条数。

```json
{
  "output_fields": {
    "show_platform": true,           // 显示操作系统平台
    "show_app_name": true,           // 显示前台应用名
    "show_display_title": true,      // 显示窗口净化标题
    "show_battery": true,           // 显示电池与充电状态
    "show_music": true,             // 显示正在播放的音乐
    "show_last_seen": true,         // 显示最后上报时间
    "show_viewer_count": false,     // 显示实时访客数
    "show_server_time": false,      // 显示服务端时间
    "show_recent_activities": false,// 显示最近活动历史片段
    "recent_activities_max": 5      // 最近活动最大展示条数（1~20）
  }
}
```

---

### ⚡ 5. 缓存配置 (`caching`)

控制插件内部的数据缓存与更新策略，有效减少重复请求，降低高频触发对上游服务器造成的负载。

- **好友面板列表缓存时长（秒） (`friend_config_cache_ttl_sec`)**:
  - 类型：`Integer`
  - 默认值：`30`
  - 范围：`0 - 600`（步长 `5`）
  - 说明：聚合查询好友面板（`/api/config` 的 `dashboards` 列表）配置数据的内存缓存有效期。
  - 提示：
    - 设为 `0` 表示禁用缓存，每次查询均实时透传请求至上游。
    - 适当保留 `30`~`60` 秒缓存可显著加快好友面板响应速度并缓解网络请求压力。

```json
{
  "caching": {
    "friend_config_cache_ttl_sec": 30 // 好友面板路由缓存 TTL（秒，0 为禁用）
  }
}
```

---

### 🛠️ 6. 命令与功能开关 (`commands`)

集中管控各子命令功能模块的启用状态与长文本截断阈值，避免消息过长或群内刷屏。

- **启用服务状态查询 (`enable_system_status_command`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：控制是否启用 `/视奸服务状态` 指令，用于快速诊断上游服务的连通性、运行时长与服务端时间。

- **启用时间线查询 (`enable_timeline_command`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：控制是否启用 `/视奸时间线`（别名 `/视奸历史`）指令，用于查询各应用的使用时长统计与活动流。

- **时间线最多展示片段数 (`timeline_max_segments`)**:
  - 类型：`Integer`
  - 默认值：`40`
  - 范围：`5 - 200`（步长 `5`）
  - 说明：时间线片段列表中最多展示的历史记录数量上限，超出部分将被折叠提示。

- **时间线展示设备名 (`timeline_show_device_names`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：控制在时间线累计时长与片段列表中是否标明设备归属；关闭后仅保留应用名称与时长。

- **启用健康数据查询 (`enable_health_command`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：控制是否启用 `/视奸健康`（别名 `/健康数据`）指令，用于查询指定日期的心率、步数、睡眠等身体指标。

- **健康数据最多展示记录数 (`health_max_records`)**:
  - 类型：`Integer`
  - 默认值：`40`
  - 范围：`5 - 200`（步长 `5`）
  - 说明：健康数据按时间段展示的最大条目数上限，防止睡眠/心率采样过多导致消息超长。

- **启用好友面板查询 (`enable_friend_command`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：控制是否启用 `/视奸好友`（别名 `/好友面板`）指令体系，用于通过只读聚合代理浏览好友的设备状态与面板数据。

```json
{
  "commands": {
    "enable_system_status_command": true, // 启用服务状态查询（/视奸服务状态）
    "enable_timeline_command": true,      // 启用时间线查询（/视奸时间线）
    "timeline_max_segments": 40,          // 时间线最多输出片段数（5~200）
    "timeline_show_device_names": true,   // 时间线是否输出设备名称
    "enable_health_command": true,        // 启用健康数据查询（/视奸健康）
    "health_max_records": 40,             // 健康数据最多输出记录数（5~200）
    "enable_friend_command": true         // 启用好友面板聚合查询（/视奸好友）
  }
}
```

---

### 📊 7. 匿名遥测 (`telemetry_config`)

为了持续优化插件在不同环境下的兼容性、及时发现上游服务结构变更或异常并统计功能使用趋势，插件集成了匿名遥测功能。

- **启用匿名遥测 (`enabled`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：控制是否开启匿名遥测数据上报。
  - 隐私保护说明：
    - **严格匿名**：仅收集随机生成的匿名实例 UUID（`.telemetry_id`）、插件版本、AstrBot/Python 版本、操作系统类型以及命令触发频次与脱敏错误日志。
    - **零业务数据上报**：**绝不**收集任何设备名、当前应用名、窗口标题、时间线历史、健康数据、好友面板名、群号、用户 ID 或聊天内容。
    - **凭据脱敏**：配置快照中已彻底剔除 `可选鉴权 Token`、黑名单关键词等私密字段。

```json
{
  "telemetry_config": {
    "enabled": true // 启用匿名遥测（默认开启，可按需关闭）
  }
}
```

---

### 📋 匹配规则与脱敏规范说明

为确保各项过滤机制精确生效，插件底层采用以下统一规范：

1. **多值分隔符兼容**：所有支持多项填写的文本框均原生支持半角逗号（`,`）、全角逗号（`，`）、半角分号（`;`）、全角分号（`；`）以及标准换行符（`\n`）混合切分，并会自动剥除首尾空白字符。
2. **设备黑白名单判定**：
   - 仅对上报数据中的 `device_name` 进行子串包含校验（大小写不敏感）。
   - 黑名单判定严格优先于白名单：若设备名命中了黑名单关键词，无论是否处于白名单中均强制隐藏。
3. **会话与群号安全匹配**：
   - `group_blacklist_sessions` 既支持完整的平台会话标识（如 `aiocqhttp:GroupMessage:123456789`），也支持直接填写群号（如 `123456789`）。
   - 填写纯群号时，插件会基于正则以 `:(群号)$` 进行后缀锚定匹配，确保不会误伤包含相同数字片段的其他会话。
4. **敏感内容读侧脱敏**：
   - 信息黑名单生效于消息渲染阶段，同时对实时叙事短语（如 `正在用XX疯狂写bug喵~` 中的应用特征）、原始 `app_name` 与 `display_title` 实施脱敏。
   - 一旦触发脱敏，相关文本字段将被统一无害化替换为设定的文案，防止隐私外泄。

</details>

## 📂 插件目录与结构

本插件采用清晰的分层结构：根目录下共 **13 个根级文件** 与 **4 个一级目录**。

- 其中 `services/` 承载业务编排与请求/渲染核心，划分为统一 HTTP 请求客户端、共享服务基类、5 个业务服务模块（实时状态、时间线、健康数据、好友面板聚合与服务状态诊断）、3 个渲染模块（实时状态、时间线与健康数据）以及匿名遥测子系统，覆盖上游通信、缓存控制、隐私脱敏与消息构建全链路。
- `utils/` 提供通用基础工具库，包含多格式配置解析、文本清洗与敏感词打码、读侧 NSFW 兜底过滤、时间格式化、环境与版本探测及启动横幅。
- `assets/` 存放插件徽章与视觉展示相关的 SVG 矢量资源。
- `.github/` 维护自动化工作流（Ruff 代码检查、质量分析、Stale 标记）、Dependabot 规则与社区协作模板（Issue / PR 模板）。

目录结构示例如下：

```bash
AstrBot/
└─ data/
   └─ plugins/
      └─ astrbot_plugin_live_dashboard/
         ├─ __init__.py                      # Python 包初始化文件，支持相对导入
         ├─ .gitignore                       # Git 忽略规则
         ├─ _conf_schema.json                # AstrBot WebUI 配置界面 schema 定义
         ├─ CHANGELOG.md                     # 插件更新日志，适用于 AstrBot v4.11.2+
         ├─ CONTRIBUTING.md                  # 本插件的贡献指南
         ├─ LICENSE                          # 许可证文件
         ├─ logo.png                         # 插件 Logo，适用于 AstrBot v4.5.0+
         ├─ main.py                          # 插件主入口文件，包含命令处理
         ├─ metadata.yaml                    # 插件元数据信息
         ├─ README.md                        # 插件说明文档
         ├─ requirements.txt                 # 插件依赖列表
         ├─ run_ruff.bat                     # Ruff 一键格式化与自动修复脚本
         │
         ├─ assets/                          # README / 仓库展示资源
         │
         ├─ services/
         │    ├─ __init__.py
         │    ├─ api_client.py               # 统一 HTTP 客户端与异常定义
         │    ├─ base_service.py             # 服务层共享基类（配置校验/异常映射/遥测注入）
         │    ├─ dashboard_service.py        # 实时状态编排层
         │    ├─ message_renderer.py         # 实时状态渲染层
         │    ├─ timeline_service.py         # 时间线编排层
         │    ├─ timeline_renderer.py        # 时间线渲染层
         │    ├─ health_service.py           # 健康数据编排层
         │    ├─ health_renderer.py          # 健康数据渲染层
         │    ├─ friend_service.py           # 好友面板聚合编排层
         │    ├─ system_status_service.py    # 服务健康检查编排层
         │    ├─ telemetry_service.py        # 匿名遥测管理器（批处理/节流/脱敏）
         │    └─ telemetry_utils.py          # 遥测安全辅助封装
         │
         └─ utils/
              ├─ __init__.py
              ├─ banner.py                   # 启动横幅
              ├─ config_parser.py            # 配置解析工具
              ├─ nsfw_filter.py              # 读侧 NSFW 过滤
              ├─ text_utils.py               # 文本清洗与敏感词打码
              ├─ time_formatter.py           # 时间与日期工具
              └─ version.py                  # 插件与 AstrBot 版本探测工具
```

### 💾 数据持久化说明

插件运行时会在 `AstrBot/data/plugin_data/astrbot_plugin_live_dashboard/` 目录下自动维护以下文件：

- `.telemetry_id`：随机生成的匿名遥测实例 UUID（跨重启保持稳定，不包含任何用户信息或设备信息）。

## 🏗️ 架构说明

```mermaid
flowchart TB
    %% ===== 样式定义 =====
    classDef user fill:#FDF6EC,stroke:#E6A23C,stroke-width:1.5px,color:#7A4E1D;
    classDef entry fill:#EEF5FF,stroke:#409EFF,stroke-width:1.5px,color:#1F3A5F;
    classDef service fill:#F0F9EB,stroke:#67C23A,stroke-width:1.5px,color:#2F4F2F;
    classDef io fill:#FFF7F2,stroke:#E67E22,stroke-width:1.5px,color:#7A4E1D;
    classDef logic fill:#F9F0FF,stroke:#9B59B6,stroke-width:1.5px,color:#4A235A;
    classDef output fill:#F5F7FA,stroke:#909399,stroke-width:1.5px,color:#303133;

    %% ===== 用户与平台层 =====
    subgraph U[用户与平台层]
      A[用户发起查询]
      B[AstrBot 事件分发]
    end

    %% ===== 入口层 =====
    subgraph E[插件入口层 · main.py]
      E1[命令入口<br/>状态 / 时间线 / 健康 / 好友 / 服务状态]
      E2[LLM 工具入口<br/>status / timeline / health / friend]
      E3[功能开关校验]
      E4[黑白名单拦截]
      E5[调用服务层]
    end

    %% ===== 业务服务层 =====
    subgraph S[业务服务层 · services/]
      S1[实时状态服务 DashboardService]
      S2[时间线服务 TimelineService]
      S3[健康数据服务 HealthService]
      S4[好友面板服务 FriendService<br/>列表 TTL 缓存]
      S5[服务健康检查 SystemStatusService]
      S6[统一异常映射 BaseService]
      S7[匿名遥测 TelemetryManager]
    end

    %% ===== 请求层 =====
    subgraph P[请求层 · api_client.py]
      P1[组装地址 + Bearer 鉴权]
      P2[httpx 请求与超时控制]
    end

    %% ===== 上游服务 =====
    subgraph UP[上游 Live Dashboard 服务]
      UP1[/api/current 实时状态]
      UP2[/api/timeline 时间线]
      UP3[/api/health-data 健康数据]
      UP4[/api/health 健康检查]
      UP5[/api/config + /api/proxy 好友聚合]
    end

    %% ===== 渲染层 =====
    subgraph R[渲染层 · renderer]
      R1[实时状态渲染 message_renderer]
      R2[时间线渲染 timeline_renderer]
      R3[健康数据渲染 health_renderer]
      R4[脱敏 / NSFW 兜底 / 截断]
    end

    %% ===== 工具层 =====
    subgraph T[工具层 · utils/]
      T1[配置解析 config_parser]
      T2[时间格式化 time_formatter]
      T3[文本处理 text_utils]
      T4[NSFW 过滤 nsfw_filter]
    end

    %% ===== 输出策略层 =====
    subgraph O[输出策略层]
      O1{多设备或长文本 且 OneBot v11}
      O2[引用 + 纯文本]
      O3[合并转发 Nodes]
      O4[命中黑名单直接拒绝]
    end

    %% ===== 数据流 =====
    A --> B
    B --> E1
    B --> E2
    E1 --> E3
    E2 --> E3
    E3 --> E4
    E4 -->|命中| O4
    E4 -->|放行| E5
    E5 --> S1
    E5 --> S2
    E5 --> S3
    E5 --> S4
    E5 --> S5
    S1 -.继承复用.-> S6
    S2 -.继承复用.-> S6
    S3 -.继承复用.-> S6
    S4 -.继承复用.-> S6
    S5 -.继承复用.-> S6
    S1 --> P1
    S2 --> P1
    S3 --> P1
    S4 --> P1
    S5 --> P1
    P1 --> P2
    P2 --> UP1
    P2 --> UP2
    P2 --> UP3
    P2 --> UP4
    P2 --> UP5
    S1 --> R1
    S2 --> R2
    S3 --> R3
    R1 --> R4
    R2 --> R4
    R3 --> R4
    T1 --> E3
    T1 --> R4
    T2 --> R4
    T3 --> R4
    T4 --> R4
    R4 -->|渲染文本| O1
    O1 -->|否| O2
    O1 -->|是| O3

    %% ===== 样式应用 =====
    class A user;
    class B,E1,E2,E3,E4,E5 entry;
    class S1,S2,S3,S4,S5,S6 service;
    class P1,P2 io;
    class UP1,UP2,UP3,UP4,UP5 io;
    class R1,R2,R3,R4 logic;
    class T1,T2,T3,T4 logic;
    class O1,O2,O3,O4 output;
```

### 📋 架构特点与细节

当前实现采用「入口层 → 业务服务层 → 请求层 / 渲染层 / 工具层」的分层设计：

- 入口层（`main.py`）：只负责 AstrBot 事件接入、命令与 LLM 工具分发、开关与黑名单校验、输出策略判定
- 业务服务层（`services/*_service.py`）：负责拉取数据、编排流程、异常映射与渲染调用，好友面板服务还内置列表 TTL 缓存
- 请求层（`services/api_client.py`）：统一封装 URL 拼接、Bearer 鉴权、httpx 请求与超时，并把异常归类为自定义异常（超时 / 网络 / 鉴权 / HTTP / 响应结构）
- 渲染层（`services/*_renderer.py`）：消费上游权威字段（`status_text`、`display_title`、`segments`、`records`），只做展示归一、合并与脱敏，不含 IO
- 工具层（`utils/`）：提供配置读取、文本清洗与敏感词打码、时间格式化、读侧 NSFW 兜底过滤等纯函数工具，并在插件加载时打印启动横幅。

**健壮的异常处理：**

- 所有服务继承 `BaseService`，按需惰性构建共享 `ApiClient`（复用同一连接池）。
- 异常按类型统一映射为用户可读提示，原始异常仅写入日志：
  - 请求超时 → 「请求超时」
  - DNS / 连接失败 → 「网络错误」
  - 401 / 403 → 「鉴权失败」
  - 其他 4xx / 5xx → 「HTTP 状态异常」
  - 响应非 JSON 对象 → 「响应异常」
  - 未预期异常 → 「发生未预期错误」
- 各命令与 LLM 工具通过 `_is_known_error` 识别服务层返回的错误前缀，避免把失败包装成成功结果。

**渲染与数据流：**

- 实时状态：`/api/current` → 设备筛选排序 → 字段开关 → 脱敏 → NSFW 兜底 → 输出文本
- 时间线：`/api/timeline` → 设备名上浮 → 相邻片段合并（`×N`）→ 标题压缩 → 截断
- 健康数据：`/api/health-data` →（并行拉取 `/api/current` 补齐设备名）→ 按设备 / 指标分组 → 单位换算
- 服务健康检查：`/api/health` → 状态 / 运行时长 / 服务端时间
- 好友面板：`/api/config` 拉取列表（TTL 缓存）→ 按名称或 id 模糊匹配 → `/api/proxy` 只读代理 → 复用上述渲染器

## ❓ 常见问题

### Q1：回复「未配置 Live Dashboard 地址」

请在插件配置中设置 `Live Dashboard 服务地址`，且不要包含尾部 `/api/current` 等接口路径，插件会自动完成子路由拼接。

### Q2：回复「鉴权失败（401/403）」

- 检查 `可选鉴权 Token` 是否正确，且与上游（或反向代理）要求的 Bearer Token 一致。
- 若上游未启用鉴权，请将 `可选鉴权 Token` 留空，避免携带错误的鉴权头。

### Q3：回复「网络错误 / 请求超时」

- 确认 `Live Dashboard 服务地址` 可从部署 AstrBot 的主机正常访问。
- 适当提高 `请求超时时间`（弱网 / 跨国场景可调至 60 秒以上）。
- 检查反向代理与防火墙是否放行目标端口。

### Q4：设备有上报但面板一直为空/离线

如果上游服务端开启了 `REQUIRE_EXPLICIT_CONSENT=1`（严格同意模式），设备 Agent 必须先通过 `/api/consent` 明确同意上报活动/健康数据，否则 `/api/report` 会被拒绝（403）。此时须在 Agent 端完成同意流程，本插件作为只读查询方无需处理同意，但面板会显示无数据。

### Q5：LLM 没有自动调用查询工具

- 确认当前会话或模型的函数调用能力。
- 确认 `Live Dashboard 服务地址` 已配置且上游服务可达，否则工具会返回失败文本而非状态原文。
- 检查对应命令功能开关未被禁用，且群或用户未被拉入黑名单。

### Q6：好友面板查询失败或找不到面板

- 确认上游 `/api/config` 的 `dashboards` 列表已聚合该面板，且面板带 `id` 字段（代理查询必需）。
- 面板名匹配为不区分大小写的子串匹配，可用面板名称或 `id` 查询。
- 若列表迟迟不更新，可适当降低缓存时长（或设为 `0` 禁用缓存）。

## 🚧 已知限制

- 当前输出格式为纯文本，尚未提供图片卡片等渲染服务。
- 实时状态 / 时间线 / 健康 / 服务状态查询未实现短时缓存（高频调用会直接请求上游，以保证数据实时性）；仅好友面板列表配置带有 TTL 缓存。
- 当前不区分会话级个性化配置（后续可按需扩展）。
- 合并转发（Nodes）仅对 OneBot v11（aiocqhttp）平台启用，其他平台的长文本会自动降级为纯文本发送。
- LLM 函数工具依赖 AstrBot 会话开启函数调用能力，若模型不支持或未开启则不会自动触发；状态工具不受命令开关约束，其余工具受对应开关限制。

## 💖 友情链接与致谢

本插件的灵感与基础服务来源于：

- [live-dashboard](https://github.com/Monika-Dream/live-dashboard)：在此感谢其开发团队对该项目的付出。

## 📚 推荐阅读

我的其他插件：

- [主动消息 (Proactive_chat)](https://github.com/Pancakes-Labs/astrbot_plugin_proactive_chat) - 它能让你的 Bot 在特定的会话长时间没有新消息后，用一个随机的时间间隔，主动发起一次拥有上下文感知、符合人设且包含动态情绪的对话。
- [灾害预警 (Disaster_Warning)](https://github.com/Pancakes-Labs/astrbot_plugin_disaster_warning) - 它能让你的 Bot 提供实时的地震、海啸、台风、气象预警信息推送服务。
- [代码统计 (Count_Loc)](https://github.com/Pancakes-Labs/astrbot_plugin_count_loc) - 它能让你的 Bot 对任意公开的 GitHub 或 GitLab 仓库的代码行数、文件数量、注释行数、物理总行数等指标进行快捷获取和分析。

## 🤝 贡献

欢迎提交 [Issue](https://github.com/Pancakes-Labs/astrbot_plugin_live_dashboard/issues) 和 [Pull Request](https://github.com/Pancakes-Labs/astrbot_plugin_live_dashboard/pulls) 来改进这个插件！

- 对于新功能的添加，请先通过 Issue 等方式讨论。
- 对于 PR (拉取请求)，请确保你已阅读并同意遵守本项目的 [贡献指南](https://github.com/Pancakes-Labs/astrbot_plugin_live_dashboard/blob/main/CONTRIBUTING.md)。

### 📞 联系我们

如果你对这个插件有任何疑问、建议或 bug 反馈，欢迎加入我的 QQ 交流群。

- **QQ 群**: 1033089808
- **群二维码**:
  
  <img width="281" alt="QQ Group QR Code" src="https://github.com/user-attachments/assets/53acb3c8-1196-4b9e-b0b3-ad3a62d5c41d" />

## 📄 许可证

GNU Affero General Public License v3.0 - 详见 [LICENSE](LICENSE) 文件。

本插件采用 AGPL v3.0 许可证，这意味着：

- 您可以自由使用、修改和分发本插件。
- 如果您在网络服务中使用本插件，必须公开源代码。
- 任何修改都必须使用相同的许可证。

## 📊 仓库状态

![Alt](https://repobeats.axiom.co/api/embed/abfee06eecd26dc40d029670a9f9d85d670d1ef3.svg "Repobeats analytics image")

## ⭐️ 星星

<a href="https://www.star-history.com/?repos=Pancakes-Labs%2Fastrbot_plugin_live_dashboard&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Pancakes-Labs/astrbot_plugin_live_dashboard&type=date&theme=dark&legend=top-left&sealed_token=ODkw1ac9dzdcu8sbITwofbXbnOuEfx7nxhnh5l5t42TaK_sUwawQuccybzVu1eDJR7tOUir7NgxHXfS-6iL5GatyautvKOwIodZ1z9ip_g5qRUfzPljVlg" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Pancakes-Labs/astrbot_plugin_live_dashboard&type=date&legend=top-left&sealed_token=ODkw1ac9dzdcu8sbITwofbXbnOuEfx7nxhnh5l5t42TaK_sUwawQuccybzVu1eDJR7tOUir7NgxHXfS-6iL5GatyautvKOwIodZ1z9ip_g5qRUfzPljVlg" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Pancakes-Labs/astrbot_plugin_live_dashboard&type=date&legend=top-left&sealed_token=ODkw1ac9dzdcu8sbITwofbXbnOuEfx7nxhnh5l5t42TaK_sUwawQuccybzVu1eDJR7tOUir7NgxHXfS-6iL5GatyautvKOwIodZ1z9ip_g5qRUfzPljVlg" />
 </picture>
</a>

---

Copyright © 2026 DBJD-CR. All rights reserved.
Released under the AGPL-3.0 License.

Made with ❤️ by DBJD-CR
