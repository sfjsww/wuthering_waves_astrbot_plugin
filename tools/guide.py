"""query_waves_guide - 对标 apps/Guide.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_guide_tool(plugin):
    @filter.llm_tool(name="query_waves_guide")
    async def query_waves_guide(self, event: AstrMessageEvent, character: str, uid: str = None):
        '''查询鸣潮角色/武器/声骸图鉴信息。

        Args:
            character(string): 角色或物品名称，如"吟霖"、"千古洑流"、"鸣钟之龟"
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
        name = plugin.wiki.get_alias(character)
        entry = await plugin.wiki.get_entry(name)
        if entry["status"]:
            record = entry["record"]
            entry_type = plugin.wiki.CATALOGUEID_MAP.get(entry["type"], "未知")
            content_url = record.get("content", {}).get("contentUrl", "")
            desc = record.get("content", {}).get("desc", "")
            if not desc:
                desc = record.get("content", {}).get("modules", [{}])[0].get("components", [{}])[0].get("content", "暂无详细说明")
            import re
            desc_clean = re.sub(r'<[^>]+>', '', desc)[:500]
            msg_parts = [f"【{entry_type}】{name}"]
            if content_url:
                msg_parts.append(f"图片: {content_url}")
            if desc_clean:
                msg_parts.append(f"说明: {desc_clean}")
            yield event.plain_result("\n".join(msg_parts))
        else:
            search = await plugin.wiki.search(character)
            if search["status"]:
                results = [r["name"] for r in search["data"].get("results", {}).get("records", [])[:10]]
                if results:
                    yield event.plain_result(f"未找到「{character}」的图鉴，您是否在找：\n" + "\n".join(results))
                else:
                    yield event.plain_result(f"未找到「{character}」的图鉴，请检查输入是否正确。")
            else:
                yield event.plain_result(entry["msg"])
    plugin.register_tool("query_waves_guide", query_waves_guide, "_tool_guide")
