"""query_waves_emoji - 对标 apps/Emoji.js"""
from astrbot.api.event import filter, AstrMessageEvent
import random


class EmojiMixin:
    @filter.llm_tool(name="query_waves_emoji")
    async def query_waves_emoji(self, event: AstrMessageEvent):
        '''获取随机鸣潮表情包。无需登录即可使用。'''
        emoji_dir = self.render.resources_dir / "emojis"
        files = list(emoji_dir.glob("*")) if emoji_dir.exists() else []
        if files:
            yield event.image_result(str(random.choice(files)))
        else:
            yield event.plain_result("暂无表情包资源。")
