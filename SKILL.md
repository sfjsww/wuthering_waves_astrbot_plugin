---
name: wuthering-waves
description: >-
  鸣潮(Wuthering Waves)游戏数据查询技能。TRIGGER when: 用户想要查询鸣潮游戏数据，
  包括角色面板、声骸评分、签到、抽卡记录、体力、数据坞、深塔、练度、图鉴、攻略、
  兑换码、卡池日历、公告、表情包、模拟抽卡、账号绑定等。
  当用户提到"鸣潮""面板""签到""抽卡""声骸""数据坞""深塔""体力""兑换码""卡池"
  "角色攻略""绑定账号""鸣潮登录"时激活。
---

# 鸣潮游戏数据查询技能

基于库街区 API 的鸣潮游戏数据查询插件，提供 24 个查询和操作工具。

## 重要：用户身份说明

多数查询操作需要用户先在 QQ 群内绑定鸣潮账号。如果用户未绑定，引导其使用 `waves_account_login` 登录。

## 工具速查

### 🔍 数据查询类（需绑定账号）

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `query_waves_character_panel` | 查询角色面板（等级、声骸评分、武器） | `character`=角色名 |
| `query_waves_user_info` | 查询玩家基本信息（昵称、等级、UID） | 无 |
| `query_waves_data_dock` | 查询数据坞（声骸收集进度） | 无 |
| `query_waves_challenge_data` | 查询全息战略等挑战数据 | 无 |
| `query_waves_exploration` | 查询各地图探索进度 | 无 |
| `query_waves_tower` | 查询逆境深塔数据 | 无 |
| `query_waves_training` | 汇总所有角色练度统计 | 无 |
| `query_waves_gacha_records` | 查询抽卡记录统计 | `card_pool_type`=角色/武器/常驻/新手 |
| `query_waves_sanity` | 查询当前体力/波片等日常数据 | 无 |

### 📖 公共查询类（无需登录）

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `query_waves_guide` | 查询角色/武器/声骸图鉴 | `character`=名称 |
| `query_waves_strategy` | 获取角色攻略图 | `character`=角色名, `provider`(可选) |
| `query_waves_calendar` | 查询活动日历和当前卡池 | 无 |
| `query_waves_news` | 查询最新游戏公告 | 无 |
| `query_waves_reward_codes` | 获取可用兑换码 | 无 |
| `query_waves_emoji` | 获取随机鸣潮表情包 | 无 |

### ⚡ 操作类

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `waves_sign_in` | 每日签到/查看签到记录 | `action`=sign/record |
| `waves_daily_task` | 查看/执行库街区每日任务 | `action`=list/do |
| `waves_simulate_gacha` | 模拟抽卡（娱乐） | `pool_type`=角色/武器, `count`=单抽/十连 |
| `waves_manage_gacha_records` | 导入/导出抽卡记录 | `action`=import/export |

### 🔑 账号管理

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `waves_account_login` | 登录/绑定鸣潮账号 | `action`=login/bind_uid |
| `waves_account_unbind` | 解绑鸣潮账号 | `uid`(可选) |
| `waves_get_token` | 查看已绑定的账号信息 | 无 |

### ⚙️ 设置与帮助

| 工具 | 用途 | 关键参数 |
|------|------|---------|
| `waves_update_settings` | 更新用户设置 | `setting`, `enabled` |
| `waves_manage_alias` | 管理角色别名 | `action`=add/delete/list |
| `waves_manage_panel_image` | 管理角色面板图 | `action`=upload/list |
| `waves_admin_user_stats` | 查看用户统计（管理员） | `action`=stats/clean_invalid |
| `waves_help` | 获取功能列表和使用帮助 | 无 |
| `waves_update_plugin` | 检查插件更新 | 无 |

## 角色名称识别

用户可能使用别名或昵称指代角色。插件内置了别名解析系统（从 `resources/Alias/` 加载），会自动处理常见的别名映射。例如：
- "安可" → 正式名
- "漂泊者" → 包含男女主角变体
- 其他社区常用的昵称和简称

直接传用户输入的字符名即可，别名由插件侧自动解析。

## 错误处理

常见错误及应对：

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| "当前没有登录任何账号" | 用户未绑定鸣潮账号 | 引导使用 `waves_account_login` |
| "Token已失效" | 登录凭证过期 | 引导重新登录 |
| "未在库街区展示该角色" | 库街区未公开该角色数据 | 引导用户在库街区APP中开启展示 |
| "查询失败，请检查对外展示开关" | 库街区数据终端板块未公开 | 引导用户在库街区设置中开启 |

## 典型对话示例

**用户:** "帮我查一下安可面板"
→ 调用 `query_waves_character_panel(character="安可")`

**用户:** "签到"
→ 调用 `waves_sign_in(action="sign")`

**用户:** "我这周抽卡怎么样"
→ 调用 `query_waves_gacha_records(card_pool_type="角色")`

**用户:** "有什么兑换码吗"
→ 调用 `query_waves_reward_codes()`

**用户:** "现在有哪些卡池"
→ 调用 `query_waves_calendar()`

**用户:** "怎么绑定账号"
→ 调用 `waves_account_login(action="login")`

**用户:** "有哪些功能"
→ 调用 `waves_help()`
