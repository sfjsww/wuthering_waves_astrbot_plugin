"""query_waves_character_panel - 对标 apps/Character.js"""
from astrbot.api.event import filter, AstrMessageEvent


class CharacterMixin:
    async def _get_account(self, event: AstrMessageEvent):
        """Helper: get user's bound account or public cookie"""
        user_id = event.get_sender_id()
        tokens = self.config_mgr.get_user_tokens(user_id)
        if tokens:
            return tokens
        public = await self.config_mgr.get_public_cookie(self.kuro)
        if public:
            return [public]
        return []

    @filter.llm_tool(name="query_waves_character_panel")
    async def query_waves_character_panel(self, event: AstrMessageEvent, character: str, uid: str = None):
        '''查询鸣潮角色面板数据（等级、声骸评分S/A/B/C/D、武器、技能）。

        Args:
            character(string): 角色名称，如"安可"、"漂泊者·湮灭"、"维里奈"、"长离"
            uid(string, optional): 玩家9位UID，不填则使用已绑定账号
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("当前没有登录任何账号，请先通过「鸣潮登录」进行账号绑定。")
            return
        name = self.wiki.get_alias(character)
        if "漂泊者" in name:
            name = "漂泊者"
        for account in tokens:
            ok = await self.kuro.is_available(account["serverId"], account["roleId"], account["token"])
            if not ok:
                yield event.plain_result(f"账号 {account.get('roleId')} 的Token已失效，请重新登录")
                continue
            role_data = await self.kuro.get_role_data(account["serverId"], account["roleId"], account["token"])
            if not role_data["status"]:
                yield event.plain_result(role_data["msg"])
                continue
            char = next((r for r in role_data["data"].get("roleList", []) if r["roleName"] == name), None)
            if not char:
                yield event.plain_result(f"UID {account['roleId']} 还未拥有 {name}")
                continue
            detail = await self.kuro.get_role_detail(account["serverId"], account["roleId"], char["roleId"], account["token"])
            if not detail["status"]:
                yield event.plain_result(detail["msg"])
                continue
            if not detail["data"].get("role"):
                yield event.plain_result(f"UID {account['roleId']} 未在库街区展示 {name}")
                continue
            from core.calculator import WeightCalculator
            detail["data"] = WeightCalculator(detail["data"], self.render.resources_dir).calculate()
            img = await self.render.render("charProfile/charProfile", {
                "uid": account["roleId"], "rolePicUrl": detail["data"]["role"].get("rolePicUrl", ""), "roleDetail": detail["data"],
            })
            yield event.image_result(img)
            return
