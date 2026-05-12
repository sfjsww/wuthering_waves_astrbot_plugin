"""waves_help - 对标 apps/Help.js"""
from astrbot.api.event import filter, AstrMessageEvent


class HelpMixin:
    @filter.llm_tool(name="waves_help")
    async def waves_help(self, event: AstrMessageEvent):
        '''获取鸣潮插件的功能列表和使用帮助。无需登录。'''
        yield event.plain_result("""鸣潮查询插件功能列表

【无需登录】
  🎲 模拟抽卡 / 📅 活动日历 / 📰 最新公告
  🎫 兑换码 / 📖 角色图鉴 / 🖼️ 角色攻略 / 😂 表情包

【需要先绑定鸣潮账号】
  📊 角色面板 / 👤 用户信息 / 🎒 数据坞
  ⚔️ 挑战数据 / 🗺️ 探索度 / 🏰 逆境深塔
  📈 练度统计 / 🎯 抽卡记录 / ⚡ 体力查询
  ✅ 每日签到 / 📋 每日任务

【账号管理】
  🔑 登录绑定 / 🔓 解绑 / 🔍 查看绑定

直接说出需求，如「查安可面板」「帮我签到」「来发十连」。""")
