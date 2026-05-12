"""query_waves_strategy - 对标 apps/Strategy.js"""
from astrbot.api.event import filter, AstrMessageEvent


class StrategyMixin:
    @filter.llm_tool(name="query_waves_strategy")
    async def query_waves_strategy(self, event: AstrMessageEvent, character: str, provider: str = "all"):
        '''获取鸣潮角色攻略图。无需登录即可使用。

        Args:
            character(string): 角色名称
            provider(string, optional): 攻略提供方，默认"all"
        '''
        name = self.wiki.get_alias(character)
        strategy_dir = self.render.resources_dir / "Strategy"
        providers = ["XMu", "moealkyne", "Linn", "ruozi"] if provider == "all" else [provider]
        for p in providers:
            p_dir = strategy_dir / p
            for ext in (".png", ".jpg", ".webp"):
                img = p_dir / f"{name}{ext}"
                if img.exists():
                    yield event.image_result(str(img))
                    return
        yield event.plain_result(f"未找到 {name} 的攻略图")
