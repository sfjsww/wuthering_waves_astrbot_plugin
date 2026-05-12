"""query_waves_calendar - 对标 apps/Calendar.js"""
from astrbot.api.event import filter, AstrMessageEvent


class CalendarMixin:
    @filter.llm_tool(name="query_waves_calendar")
    async def query_waves_calendar(self, event: AstrMessageEvent):
        '''查询鸣潮活动日历和当前卡池信息。无需登录即可使用。'''
        data = await self.kuro.get_event_list()
        if data["status"]:
            img = await self.render.render("calendar/calendar", {"data": data["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(data["msg"])
