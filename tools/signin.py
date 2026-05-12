"""waves_sign_in - 对标 apps/SignIn.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_signin_tool(plugin):
    @filter.llm_tool(name="waves_sign_in")
    async def waves_sign_in(self, event: AstrMessageEvent, action: str):
        '''执行鸣潮每日签到或查看签到记录。Args: action(string): "sign"=执行签到, "record"=查看签到记录'''
        user_id = event.get_sender_id()
        tokens = plugin.config_mgr.get_user_tokens(user_id)
        if not tokens:
            yield event.plain_result("当前没有登录任何账号，请先通过「鸣潮登录」进行账号绑定。")
            return
        if action == "sign":
            results = []
            for account in tokens:
                ok = await plugin.kuro.is_available(account["serverId"], account["roleId"], account["token"])
                if not ok:
                    results.append(f"账号 {account.get('roleId')} 的Token已失效")
                    continue
                sign = await plugin.kuro.sign_in(account["serverId"], account["roleId"], account.get("userId", account["roleId"]), account["token"])
                rec = await plugin.kuro.query_record(account["serverId"], account["roleId"], account["token"])
                if sign["status"] and rec["status"]:
                    goods = rec["data"][0] if rec["data"] else {}
                    results.append(f"签到成功！获得「{goods.get('goodsName', '?')} × {goods.get('goodsNum', '?')}」")
                else:
                    results.append(f"签到失败：{sign.get('msg', '未知错误')}")
            yield event.plain_result("\n".join(results))
        elif action == "record":
            for account in tokens[:1]:
                ok = await plugin.kuro.is_available(account["serverId"], account["roleId"], account["token"])
                if not ok:
                    yield event.plain_result(f"账号 {account.get('roleId')} 的Token已失效")
                    continue
                record = await plugin.kuro.query_record(account["serverId"], account["roleId"], account["token"])
                if record["status"]:
                    record["data"] = record["data"][:50]
                    img = await plugin.render.render("queryRecord/queryRecord", {"listData": record["data"]})
                    yield event.image_result(img)
                else:
                    yield event.plain_result(record["msg"])
        else:
            yield event.plain_result("请指定 action: sign(签到) / record(签到记录)")
    plugin.register_tool("waves_sign_in", waves_sign_in, "_tool_signin")
