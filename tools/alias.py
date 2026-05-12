"""waves_manage_alias - 对标 apps/Alias.js"""
from astrbot.api.event import filter, AstrMessageEvent
import yaml

def register_alias_tool(plugin):
    @filter.llm_tool(name="waves_manage_alias")
    async def waves_manage_alias(self, event: AstrMessageEvent, action: str, character: str = "", alias: str = ""):
        '''管理角色别名。Args: action(string): "add"/"delete"/"list", character(string): 角色名, alias(string): 别名'''
        custom_dir = plugin.render.resources_dir / "Alias" / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)
        custom_file = custom_dir / "custom.yaml"
        data = {}
        if custom_file.exists():
            with open(custom_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        if action == "add":
            data.setdefault(character, [])
            if alias not in data[character]:
                data[character].append(alias)
            with open(custom_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            yield event.plain_result(f"已为 {character} 添加别名: {alias}")
        elif action == "delete":
            if character in data and alias in data[character]:
                data[character].remove(alias)
                with open(custom_file, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True)
                yield event.plain_result(f"已删除 {character} 的别名: {alias}")
            else:
                yield event.plain_result(f"未找到 {character} 的别名 {alias}")
        elif action == "list":
            name = plugin.wiki.get_alias(character) if character else ""
            if name in data:
                yield event.plain_result(f"{name} 的别名: {', '.join(data[name])}")
            else:
                yield event.plain_result(f"{character or name} 暂无自定义别名")
        else:
            yield event.plain_result("请指定 action: add / delete / list")
    plugin.register_tool("waves_manage_alias", waves_manage_alias, "_tool_alias")
