"""query_waves_calendar - 对标 apps/Calendar.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_calendar_tool(plugin):
    @filter.llm_tool(name="query_waves_calendar")
    async def query_waves_calendar(self, event: AstrMessageEvent):
        '''查询鸣潮活动日历和当前卡池信息。'''
        user_id = event.get_sender_id()
        tokens = plugin.config_mgr.get_user_tokens(user_id)
        if not tokens:
            public = await plugin.config_mgr.get_public_cookie(plugin.kuro)
            if not public:
                yield event.plain_result("当前没有登录任何账号，请先绑定账号。")
                return
            tokens = [public]
        account = tokens[0]
        ok = await plugin.kuro.is_available(account["serverId"], account["roleId"], account["token"])
        if not ok:
            yield event.plain_result(f"账号 {account.get('roleId')} 的Token已失效")
            return
        data = await plugin.kuro.get_event_list()
        if data["status"]:
            img = await plugin.render.render("calendar/calendar", {"data": data["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(data["msg"])
    plugin.register_tool("query_waves_calendar", query_waves_calendar, "_tool_calendar")
