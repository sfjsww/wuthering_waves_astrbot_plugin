"""query_waves_character_panel - 对标 apps/Character.js"""
from astrbot.api.event import filter, AstrMessageEvent
import asyncio

def register_character_tool(plugin):
    @filter.llm_tool(name="query_waves_character_panel")
    async def query_waves_character_panel(self, event: AstrMessageEvent, character: str, uid: str = None):
        '''查询鸣潮角色面板数据，包括角色等级、声骸评分(S/A/B/C/D)、武器、技能等信息。

        Args:
            character(string): 角色名称，如"安可"、"漂泊者·湮灭"、"维里奈"、"长离"
            uid(string, optional): 玩家9位数字UID，不填则使用当前QQ用户已绑定的第一账号
        '''
        user_id = event.get_sender_id()
        tokens = plugin.config_mgr.get_user_tokens(user_id)
        if not tokens:
            public = await plugin.config_mgr.get_public_cookie(plugin.kuro)
            if not public:
                yield event.plain_result("当前没有登录任何账号，请先绑定账号。")
                return
            tokens = [public]
        name = plugin.wiki.get_alias(character)
        if "漂泊者" in name:
            name = "漂泊者"
        msgs = []
        for account in tokens:
            ok = await plugin.kuro.is_available(account["serverId"], account["roleId"], account["token"])
            if not ok:
                msgs.append(f"账号 {account.get('roleId')} 的Token已失效")
                continue
            role_data = await plugin.kuro.get_role_data(account["serverId"], account["roleId"], account["token"])
            if not role_data["status"]:
                msgs.append(role_data["msg"])
                continue
            char = next((r for r in role_data["data"].get("roleList", []) if r["roleName"] == name), None)
            if not char:
                msgs.append(f"UID {account['roleId']} 还未拥有 {name}")
                continue
            detail = await plugin.kuro.get_role_detail(account["serverId"], account["roleId"], char["roleId"], account["token"])
            if not detail["status"]:
                msgs.append(detail["msg"])
                continue
            if not detail["data"].get("role"):
                msgs.append(f"UID {account['roleId']} 未在库街区展示 {name}")
                continue
            from core.calculator import WeightCalculator
            detail["data"] = WeightCalculator(detail["data"], plugin.render.resources_dir).calculate()
            img = await plugin.render.render("charProfile/charProfile", {
                "uid": account["roleId"], "rolePicUrl": detail["data"]["role"].get("rolePicUrl", ""), "roleDetail": detail["data"],
            })
            yield event.image_result(img)
        if msgs:
            yield event.plain_result("\n".join(msgs))
    plugin.register_tool("query_waves_character_panel", query_waves_character_panel, "_tool_character")
