# 鸣潮 Waves 查询插件 (AstrBot)

基于库街区 API 的鸣潮游戏数据查询插件，提供 **29 个 LLM 可调用工具**，支持角色面板、声骸评分、签到、抽卡记录、数据坞、深塔等全部功能。

## 安装

在 AstrBot 插件市场中搜索 `wuthering_waves_astrbot_plugin` 安装，或手动将本仓库克隆到 `data/plugins/` 目录。

```bash
cd data/plugins
git clone https://github.com/sfjsww/wuthering_waves_astrbot_plugin.git
pip install -r requirements.txt
```

### 渲染引擎依赖

插件使用 Node.js 子进程进行 HTML 渲染（`art-template` + `Puppeteer`）：

```bash
cd data/plugins/wuthering_waves_astrbot_plugin
npm install art-template puppeteer
```

确保系统已安装 Chromium 或通过环境变量 `CHROMIUM_PATH` 指定路径。

## 功能概览

### 数据查询（需绑定账号）

| 工具 | 用途 |
|------|------|
| `query_waves_character_panel` | 查询角色面板（等级、声骸评分 S/A/B/C/D、武器、技能） |
| `query_waves_user_info` | 查询玩家基本信息（昵称、等级、UID、角色列表） |
| `query_waves_data_dock` | 查询数据坞（声骸收集进度） |
| `query_waves_challenge_data` | 查询全息战略等挑战数据 |
| `query_waves_exploration` | 查询各地图探索进度 |
| `query_waves_tower` | 查询逆境深塔数据 |
| `query_waves_training` | 汇总所有角色练度统计 |
| `query_waves_gacha_records` | 查询抽卡记录统计（缓存模式） |
| `query_waves_sanity` | 查询当前体力/波片等日常数据 |

### 公共查询（无需登录）

| 工具 | 用途 |
|------|------|
| `query_waves_calendar` | 查询活动日历和当前卡池 |
| `query_waves_news` | 查询最新游戏公告和活动资讯 |
| `query_waves_reward_codes` | 获取当前可用兑换码 |
| `query_waves_guide` | 查询角色/武器/声骸图鉴 |
| `query_waves_strategy` | 获取角色攻略图（支持多来源） |
| `query_waves_emoji` | 获取随机鸣潮表情包 |

### 操作工具

| 工具 | 用途 |
|------|------|
| `waves_sign_in` | 执行每日签到 / 查看签到记录 |
| `waves_daily_task` | 查看库街区每日任务 |
| `waves_simulate_gacha` | 模拟抽卡（仅供娱乐） |
| `waves_manage_gacha_records` | 导入/导出抽卡记录（支持 Client.log、URL、JSON 多种格式） |
| `get_qq_file_content` | 自动从 QQ 聊天记录获取用户发送的文件内容 |

### 账号管理

| 工具 | 用途 |
|------|------|
| `waves_account_login` | 网页验证码登录 / 绑定游戏 UID |
| `waves_account_unbind` | 解绑鸣潮账号 |
| `waves_get_token` | 查看已绑定账号信息（不暴露 Token 明文） |

### 设置与维护

| 工具 | 用途 |
|------|------|
| `waves_update_settings` | 配置自动签到/体力推送/公告推送 |
| `waves_manage_alias` | 管理角色别名 |
| `waves_manage_panel_image` | 管理角色面板图 |
| `waves_admin_user_stats` | 查看用户统计 / 清理失效账号（管理员） |
| `waves_help` | 获取功能列表和使用帮助 |
| `waves_update_plugin` | 检查插件更新 |

## 配置项

所有配置均可通过 AstrBot WebUI 修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `reverse_proxy_url` | `https://api.kurobbs.com` | 库街区 API 反向代理地址 |
| `proxy_url` | (空) | HTTP 代理地址 |
| `use_public_cookie` | `true` | 允许未绑定用户共享公共 Token 查询 |
| `allow_login` | `false` | 允许网页验证码登录 |
| `server_port` | `25088` | 登录服务器端口 |
| `public_link` | `http://127.0.0.1:25088` | 登录服务公开地址 |
| `render_scale` | `100` | 图片渲染精度（50-200） |
| `signin_interval` | `37` | 自动签到间隔（秒） |
| `enable_log` | `false` | 输出成功日志 |

## 使用流程

1. **绑定账号**：发送「鸣潮登录」获取验证码登录链接，或使用「绑定UID」直接绑定
2. **查询数据**：绑定后可直接描述需求，如「查安可面板」「签到」「查深塔」
3. **导入抽卡**：发送 Client.log 文件后使用「导入抽卡记录」，或直接粘贴 URL/JSON

## 角色别名

插件内置了角色别名系统（`resources/Alias/`），自动识别社区常用昵称和简称。可通过 `waves_manage_alias` 添加自定义别名。

## 定时任务

插件内置 4 个定时任务，需在配置中启用：

- **自动签到**：每日 0:10 执行
- **自动任务**：每日 6:00 执行
- **体力推送**：每 7 分钟检查体力是否满
- **公告推送**：每 15 分钟检查新公告

## 鸣谢

- 原项目 [waves-plugin](https://github.com/sfjsww/waves-plugin)（Yunzai/Trss 版）
- [库街区](https://www.kurobbs.com/) API

## 许可

本项目仅供学习交流使用，不得用于商业用途。
