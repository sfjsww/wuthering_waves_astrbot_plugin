"""query_waves_gacha_records + waves_manage_gacha_records - 对标 apps/Gacha.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_gacha_tools(plugin):
    @filter.llm_tool(name="query_waves_gacha_records")
    async def query_waves_gacha_records(self, event: AstrMessageEvent, card_pool_type: str = "", uid: str = None):
        '''查询鸣潮抽卡记录统计和分析。

        Args:
            card_pool_type(string, optional): 卡池类型，"角色"、"武器"、"常驻"、"新手"等
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
        pool_map = {"角色": 1, "武器": 2, "常驻角色": 3, "常驻武器": 4, "新手": 5, "自选": 6}
        pool_type = pool_map.get(card_pool_type, 0)
        query = {"serverId": account["serverId"], "playerId": account["roleId"], "cardPoolType": pool_type, "languageCode": "zh-Hans"}
        data = await plugin.kuro.get_gacha(query)
        if data["status"]:
            img = await plugin.render.render("gacha/gacha", {"gachaData": data["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(data["msg"])

    @filter.llm_tool(name="waves_manage_gacha_records")
    async def waves_manage_gacha_records(self, event: AstrMessageEvent, action: str, data: str = None):
        '''导入或导出抽卡记录。

        Args:
            action(string): "import"或"export"
            data(string, optional): 导入时提供JSON数据
        '''
        if action == "export":
            user_id = event.get_sender_id()
            tokens = plugin.config_mgr.get_user_tokens(user_id)
            if not tokens:
                yield event.plain_result("当前没有登录任何账号。")
                return
            account = tokens[0]
            cached = plugin.config_mgr.get_gacha_records(account.get("roleId", ""))
            if cached:
                import json
                yield event.plain_result(f"抽卡记录导出:\n```json\n{json.dumps(cached, ensure_ascii=False, indent=2)[:4000]}\n```")
            else:
                yield event.plain_result("暂无抽卡记录缓存，请先查询抽卡记录。")
        elif action == "import":
            yield event.plain_result("导入功能需要先在WebUI中开启 allow_import 配置。")
        else:
            yield event.plain_result("请指定 action: import 或 export")

    plugin.register_tool("query_waves_gacha_records", query_waves_gacha_records, "_tool_gacha_query")
    plugin.register_tool("waves_manage_gacha_records", waves_manage_gacha_records, "_tool_gacha_manage")
