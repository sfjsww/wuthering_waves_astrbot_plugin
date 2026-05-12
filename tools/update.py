"""waves_update_plugin - 对标 apps/Update.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_update_tool(plugin):
    @filter.llm_tool(name="waves_update_plugin")
    async def waves_update_plugin(self, event: AstrMessageEvent):
        '''检查鸣潮插件更新。'''
        yield event.plain_result("鸣潮查询插件 v1.0.0\n检查更新请访问: https://github.com/sfjsww/wuthering_waves_astrbot_plugin")
    plugin.register_tool("waves_update_plugin", waves_update_plugin, "_tool_update")
