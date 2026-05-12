"""waves_account_login + waves_account_unbind + waves_get_token - 对标 apps/Bind.js"""
from astrbot.api.event import filter, AstrMessageEvent
import uuid

def register_account_tools(plugin):
    @filter.llm_tool(name="waves_account_login")
    async def waves_account_login(self, event: AstrMessageEvent, action: str = "login", code: str = None):
        '''登录或绑定鸣潮账号。Args: action(string): "login"=获取登录链接, "bind_uid"=绑定UID, code(string, optional): 绑定码'''
        user_id = event.get_sender_id()
        if action == "login":
            login_id = uuid.uuid4().hex[:12]
            url = plugin.login_server.create_login_session(login_id, user_id, user_id)
            yield event.plain_result(f"请在浏览器中打开以下链接完成登录（有效期10分钟）：\n{url}")
        elif action == "bind_uid":
            if code:
                # Simple binding: store the UID directly
                tokens = plugin.config_mgr.get_user_tokens(user_id)
                tokens.append({"serverId": "76402e5b20be2c39f095a152090afddc", "roleId": code, "userId": code, "token": ""})
                plugin.config_mgr.set_user_tokens(user_id, tokens)
                yield event.plain_result(f"已绑定UID: {code}")
            else:
                yield event.plain_result("请提供要绑定的UID或特征码。")
        else:
            yield event.plain_result("请指定 action: login / bind_uid")

    @filter.llm_tool(name="waves_account_unbind")
    async def waves_account_unbind(self, event: AstrMessageEvent, uid: str = None):
        '''解绑鸣潮账号。Args: uid(string, optional): 要解绑的UID，不填则解绑全部'''
        user_id = event.get_sender_id()
        tokens = plugin.config_mgr.get_user_tokens(user_id)
        if not tokens:
            yield event.plain_result("当前没有绑定的账号。")
            return
        if uid:
            tokens = [t for t in tokens if t.get("roleId") != uid]
            plugin.config_mgr.set_user_tokens(user_id, tokens)
            yield event.plain_result(f"已解绑 UID: {uid}")
        else:
            plugin.config_mgr.set_user_tokens(user_id, [])
            yield event.plain_result("已解绑全部账号。")

    @filter.llm_tool(name="waves_get_token")
    async def waves_get_token(self, event: AstrMessageEvent):
        '''查看当前已绑定的鸣潮账号信息。'''
        user_id = event.get_sender_id()
        tokens = plugin.config_mgr.get_user_tokens(user_id)
        if not tokens:
            yield event.plain_result("当前没有绑定的账号。")
            return
        info = []
        for t in tokens:
            masked = t.get("token", "")
            info.append(f"UID: {t.get('roleId', '?')} | 服务器: {t.get('serverId', '?')[:8]}...")
        yield event.plain_result("已绑定的账号：\n" + "\n".join(info))

    plugin.register_tool("waves_account_login", waves_account_login, "_tool_account_login")
    plugin.register_tool("waves_account_unbind", waves_account_unbind, "_tool_account_unbind")
    plugin.register_tool("waves_get_token", waves_get_token, "_tool_get_token")
