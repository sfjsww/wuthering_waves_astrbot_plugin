"""waves_admin_user_stats - 对标 apps/Manage.js"""
from astrbot.api.event import filter, AstrMessageEvent


class AdminMixin:
    @filter.llm_tool(name="waves_admin_user_stats")
    async def waves_admin_user_stats(self, event: AstrMessageEvent, action: str = "stats"):
        '''管理插件用户数据（管理员功能）。

        Args:
            action(string): "stats"=查看统计, "clean_invalid"=清理失效账号
        '''
        if action == "stats":
            users = self.config_mgr.get_all_bound_users()
            total_tokens = sum(len(v) for v in users.values())
            yield event.plain_result(f"已绑定用户数: {len(users)}\n总绑定账号数: {total_tokens}")
        elif action == "clean_invalid":
            count = 0
            users = self.config_mgr.get_all_bound_users()
            for user_id, tokens in users.items():
                valid = []
                for t in tokens:
                    if t.get("token"):
                        try:
                            ok = await self.kuro.is_available(t["serverId"], t["roleId"], t["token"])
                            if ok:
                                valid.append(t)
                            else:
                                count += 1
                        except Exception:
                            valid.append(t)
                    else:
                        valid.append(t)
                self.config_mgr.set_user_tokens(user_id, valid)
            yield event.plain_result(f"已清理 {count} 个失效账号。")
        else:
            yield event.plain_result("请指定 action: stats / clean_invalid")
