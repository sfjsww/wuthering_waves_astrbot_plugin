"""query_waves_reward_codes - 对标 apps/Reward.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_reward_tool(plugin):
    @filter.llm_tool(name="query_waves_reward_codes")
    async def query_waves_reward_codes(self, event: AstrMessageEvent):
        '''查询鸣潮当前可用的兑换码。'''
        try:
            events = await plugin.kuro.get_event_list()
            if events["status"]:
                codes = []
                for ev in events["data"].get("list", []):
                    for code in ev.get("exchangeCodes", []):
                        codes.append(f"{code.get('code', '?')} - {code.get('name', '?')}")
                if codes:
                    yield event.plain_result("当前可用的兑换码:\n" + "\n".join(codes))
                else:
                    yield event.plain_result("当前没有可用的兑换码。")
            else:
                yield event.plain_result("查询兑换码失败，请稍后重试。")
        except Exception as e:
            yield event.plain_result(f"查询失败: {e}")
    plugin.register_tool("query_waves_reward_codes", query_waves_reward_codes, "_tool_reward")
