"""query_waves_reward_codes - 对标 apps/Reward.js"""
from astrbot.api.event import filter, AstrMessageEvent


class RewardMixin:
    @filter.llm_tool(name="query_waves_reward_codes")
    async def query_waves_reward_codes(self, event: AstrMessageEvent):
        '''查询鸣潮当前可用的兑换码。无需登录即可使用。'''
        try:
            data = await self.kuro.get_event_list()
            if data["status"]:
                codes = []
                for ev in data["data"].get("list", []):
                    for code in ev.get("exchangeCodes", []):
                        codes.append(f"{code.get('code', '?')} — {code.get('name', code.get('desc', '兑换码'))}")
                if codes:
                    yield event.plain_result("当前可用的兑换码：\n" + "\n".join(codes))
                else:
                    yield event.plain_result("当前没有可用的兑换码。")
            else:
                yield event.plain_result("查询兑换码失败，请稍后重试。")
        except Exception as e:
            yield event.plain_result(f"查询失败: {e}")
