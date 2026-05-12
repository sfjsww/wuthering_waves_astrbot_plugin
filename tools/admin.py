"""waves_admin_user_stats - 对标 apps/Manage.js"""
from astrbot.api.event import filter, AstrMessageEvent

def register_admin_tool(plugin):
    @filter.llm_tool(name="waves_admin_user_stats")
    async def waves_admin_user_stats(self, event: AstrMessageEvent, action: str = "stats"):
        '''管理插件用户数据（管理员功能）。Args: action(string): "stats"=查看统计, "clean_invalid"=清理失效账号'''
        if action == "stats":
            users = plugin.config_mgr.get_all_bound_users()
            total_tokens = sum(len(v) for v in users.values())
            yield event.plain_result(f"已绑定用户数: {len(users)}\n总绑定账号数: {total_tokens}")
        elif action == "clean_invalid":
            count = 0
            users = plugin.config_mgr.get_all_bound_users()
            for user_id, tokens in users.items():
                valid = []
                for t in tokens:
                    if t.get("token"):
                        try:
                            ok = await plugin.kuro.is_available(t["serverId"], t["roleId"], t["token"])
                            if ok:
                                valid.append(t)
                            else:
                                count += 1
                        except Exception:
                            valid.append(t)  # Keep on network error
                    else:
                        valid.append(t)  # Keep tokens without tokens (uid-only binds)
                plugin.config_mgr.set_user_tokens(user_id, valid)
            yield event.plain_result(f"已清理 {count} 个失效账号。")
        else:
            yield event.plain_result("请指定 action: stats / clean_invalid")
    plugin.register_tool("waves_admin_user_stats", waves_admin_user_stats, "_tool_admin")
