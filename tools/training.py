"""query_waves_training - 对标 apps/Training.js"""
from astrbot.api.event import filter, AstrMessageEvent
import asyncio


class TrainingMixin:
    @filter.llm_tool(name="query_waves_training")
    async def query_waves_training(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮所有角色练度统计汇总。

        Args:
            uid(string, optional): 9位数字UID，不填则使用当前用户已绑定的第一账号
        '''
        user_id = event.get_sender_id()
        tokens = self.config_mgr.get_user_tokens(user_id)
        if not tokens:
            public = await self.config_mgr.get_public_cookie(self.kuro)
            if not public:
                yield event.plain_result("当前没有登录任何账号，请先绑定账号。")
                return
            tokens = [public]
        account = tokens[0]
        ok = await self.kuro.is_available(account["serverId"], account["roleId"], account["token"])
        if not ok:
            yield event.plain_result(f"账号 {account.get('roleId')} 的Token已失效")
            return
        role_data = await self.kuro.get_role_data(account["serverId"], account["roleId"], account["token"])
        if not role_data["status"]:
            yield event.plain_result(role_data["msg"])
            return
        roles = role_data["data"].get("roleList", [])
        tasks = [self.kuro.get_role_detail(account["serverId"], account["roleId"], r["roleId"], account["token"]) for r in roles]
        details = await asyncio.gather(*tasks)
        valid = [d["data"] for d in details if d["status"] and d["data"].get("role")]
        if not valid:
            yield event.plain_result("未在库街区展示任何角色")
            return
        img = await self.render.render("training/training", {"roleData": role_data["data"], "roleDetails": valid})
        yield event.image_result(img)
