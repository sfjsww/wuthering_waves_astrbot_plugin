"""query_waves_guide - 对标 apps/Guide.js"""
from astrbot.api.event import filter, AstrMessageEvent


class GuideMixin:
    @filter.llm_tool(name="query_waves_guide")
    async def query_waves_guide(self, event: AstrMessageEvent, character: str):
        '''查询鸣潮角色/武器/声骸图鉴信息。无需登录即可使用。

        Args:
            character(string): 名称，如"安可"、"维里奈"
        '''
        name = self.wiki.get_alias(character)
        result = await self.wiki.get_entry(name)
        if result["status"]:
            record = result["record"]
            text = f"【{name}】\n分类: {self.wiki.CATALOGUEID_MAP.get(result.get('type', ''), '?')}\n"
            for seg in record.get("segments", []):
                for item in seg.get("items", []):
                    if item.get("key") and item.get("value"):
                        text += f"{item['key']}: {item['value']}\n"
            yield event.plain_result(text[:2000])
        else:
            yield event.plain_result(f"未找到「{name}」的图鉴信息")
