"""query_waves_news - 对标 apps/News.js"""
from astrbot.api.event import filter, AstrMessageEvent


class NewsMixin:
    @filter.llm_tool(name="query_waves_news")
    async def query_waves_news(self, event: AstrMessageEvent, news_type: str = ""):
        '''查询鸣潮最新游戏公告和活动资讯。

        Args:
            news_type(string, optional): 资讯类型，"活动"/"公告"/"资讯"，不填则获取全部
        '''
        type_map = {"活动": 1, "资讯": 2, "公告": 3}
        event_type = type_map.get(news_type, 0)
        data = await self.kuro.get_event_list(event_type)
        if data["status"]:
            items = data["data"].get("list", [])[:20]
            if not items:
                yield event.plain_result("暂无相关资讯。")
                return
            lines = []
            for item in items:
                title = item.get("postTitle", "无标题")
                post_id = item.get("postId", "")
                pub_time = item.get("publishTime", "")
                url = f"https://www.kurobbs.com/mc/post/{post_id}" if post_id else ""
                time_str = ""
                if pub_time:
                    from datetime import datetime
                    try:
                        dt = datetime.fromtimestamp(pub_time / 1000)
                        time_str = dt.strftime("%Y-%m-%d %H:%M")
                    except (TypeError, ValueError):
                        time_str = str(pub_time)
                line = f"{title}"
                if time_str:
                    line += f"\n  时间: {time_str}"
                if url:
                    line += f"\n  链接: {url}"
                lines.append(line)
            type_label = news_type if news_type else "全部"
            yield event.plain_result(f"【{type_label}资讯】共{len(lines)}条:\n\n" + "\n---\n".join(lines))
        else:
            yield event.plain_result(data["msg"])
