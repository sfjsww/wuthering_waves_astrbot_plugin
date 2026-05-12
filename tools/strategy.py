"""query_waves_strategy - 对标 apps/Strategy.js"""
from astrbot.api.event import filter, AstrMessageEvent
from pathlib import Path

def register_strategy_tool(plugin):
    @filter.llm_tool(name="query_waves_strategy")
    async def query_waves_strategy(self, event: AstrMessageEvent, character: str, provider: str = "all"):
        '''获取鸣潮角色攻略图。

        Args:
            character(string): 角色名称，如"今汐"、"长离"、"维里奈"
            provider(string, optional): 图片来源，"all"/"XMu"/"moealkyne"/"Linn"/"ruozi"
        '''
        name = plugin.wiki.get_alias(character)
        strategy_dir = plugin.render.resources_dir / "Strategy"
        providers = ["XMu", "moealkyne", "Linn", "ruozi"] if provider == "all" else [provider]
        found = False
        for p in providers:
            p_dir = strategy_dir / p
            for ext in (".png", ".jpg", ".webp"):
                img = p_dir / f"{name}{ext}"
                if img.exists():
                    yield event.image_result(str(img))
                    found = True
        if not found:
            yield event.plain_result(f"未找到 {name} 的攻略图（提供方: {provider}）")
    plugin.register_tool("query_waves_strategy", query_waves_strategy, "_tool_strategy")
