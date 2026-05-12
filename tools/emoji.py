"""query_waves_emoji - 对标 apps/Emoji.js"""
from astrbot.api.event import filter, AstrMessageEvent
import random

def register_emoji_tool(plugin):
    @filter.llm_tool(name="query_waves_emoji")
    async def query_waves_emoji(self, event: AstrMessageEvent):
        '''获取随机鸣潮表情包。'''
        emoji_dir = plugin.render.resources_dir / "emojis"
        files = list(emoji_dir.glob("*")) if emoji_dir.exists() else []
        if files:
            chosen = random.choice(files)
            yield event.image_result(str(chosen))
        else:
            yield event.plain_result("暂无表情包资源。")
    plugin.register_tool("query_waves_emoji", query_waves_emoji, "_tool_emoji")
