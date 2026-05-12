"""waves_help - 对标 apps/Help.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_help_tool(plugin):
    @filter.llm_tool(name="waves_help")
    async def waves_help(self, event: AstrMessageEvent):
        '''获取鸣潮插件的功能列表和使用帮助。当用户不清楚有哪些功能或如何使用时可调用。'''
        help_text = """**鸣潮查询插件功能列表**

查询类:
- 角色面板 — 查询角色等级、声骸评分、武器等详情
- 用户信息 — 查询玩家基本信息、等级、角色列表
- 数据坞 — 查询声骸收集进度
- 挑战数据 — 查询全息战略等挑战数据
- 探索度 — 查询各地图探索进度
- 逆境深塔 — 查询深塔挑战数据
- 练度统计 — 汇总所有角色练度
- 抽卡记录 — 查询抽卡统计和分析
- 体力/日常数据 — 查询当前体力等日常数据
- 图鉴 — 查询角色/武器/声骸图鉴
- 攻略 — 获取角色攻略图
- 日历/卡池 — 查询活动日历和当前卡池
- 公告 — 查询最新游戏公告
- 兑换码 — 获取可用兑换码

操作类:
- 签到 — 每日签到获取奖励
- 每日任务 — 执行库街区每日任务
- 模拟抽卡 — 娱乐性模拟抽卡

账号:
- 登录/绑定 — 绑定鸣潮游戏账号

设置:
- 自动签到/任务/推送开关
- 别名管理
- 面板图管理

直接描述你的需求，例如「帮我查一下安可面板」「帮我签到」「查一下我的抽卡记录」，我会自动调用对应功能。"""
        yield event.plain_result(help_text)
    plugin.register_tool("waves_help", waves_help, "_tool_help")
