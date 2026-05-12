"""waves_daily_task - 对标 apps/Task.js"""
from astrbot.api.event import filter, AstrMessageEvent


class DailyTaskMixin:
    @filter.llm_tool(name="waves_daily_task")
    async def waves_daily_task(self, event: AstrMessageEvent, action: str = "list"):
        '''管理鸣潮库街区每日任务。

        Args:
            action(string): "do"=执行任务, "list"=查看任务列表
        '''
        user_id = event.get_sender_id()
        tokens = self.config_mgr.get_user_tokens(user_id)
        if not tokens:
            yield event.plain_result("当前没有登录任何账号，请先绑定账号。")
            return
        account = tokens[0]
        ok = await self.kuro.is_available(account["serverId"], account["roleId"], account["token"])
        if not ok:
            yield event.plain_result(f"账号 {account.get('roleId')} 的Token已失效")
            return
        if action == "do":
            yield event.plain_result("每日任务执行功能正在开发中，请通过库街区APP手动完成任务。")
        elif action == "list":
            data = await self.kuro.get_game_data(account["token"])
            if data["status"]:
                img = await self.render.render("taskList/taskList", {"data": data["data"]})
                yield event.image_result(img)
            else:
                yield event.plain_result(data["msg"])
        else:
            yield event.plain_result("请指定 action: do(执行任务) / list(任务列表)")
