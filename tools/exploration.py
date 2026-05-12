"""query_waves_exploration - 对标 apps/Explore.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_exploration_tool(plugin):
    @filter.llm_tool(name="query_waves_exploration")
    async def query_waves_exploration(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮各地图探索进度数据。

        Args:
            uid(string, optional): 9位数字UID，不填则使用当前用户已绑定的第一账号
        '''
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
        data = await plugin.kuro.get_explore_data(account["serverId"], account["roleId"], account["token"])
        if data["status"]:
            img = await plugin.render.render("exploreIndex/exploreIndex", {"data": data["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(data["msg"])
    plugin.register_tool("query_waves_exploration", query_waves_exploration, "_tool_exploration")
