"""waves_manage_panel_image - 对标 apps/imgUpload.js"""
from astrbot.api.event import filter, AstrMessageEvent
from pathlib import Path
import shutil

def register_panel_image_tool(plugin):
    @filter.llm_tool(name="waves_manage_panel_image")
    async def waves_manage_panel_image(self, event: AstrMessageEvent, action: str, character: str = "", index: int = 0):
        '''管理角色面板图。Args: action(string): "upload"/"list"/"original"/"delete", character(string): 角色名, index(int, optional): 删除时的序号'''
        role_pic_dir = plugin.render.resources_dir / "rolePic"
        if action == "list":
            if character:
                char_dir = role_pic_dir / character
                files = list(char_dir.glob("*")) if char_dir.exists() else []
                if files:
                    yield event.plain_result(f"{character} 的面板图 ({len(files)}张):\n" + "\n".join(f"  {i}. {f.name}" for i, f in enumerate(files, 1)))
                else:
                    yield event.plain_result(f"{character} 暂无面板图")
            else:
                dirs = [d.name for d in role_pic_dir.iterdir() if d.is_dir()]
                yield event.plain_result("已有面板图的角色:\n" + "\n".join(dirs) if dirs else "暂无面板图")
        elif action == "original":
            yield event.plain_result("请发送带有面板图的图片消息以获取原图。")
        elif action == "delete":
            yield event.plain_result("删除功能需要管理员权限。")
        else:
            yield event.plain_result("请指定 action: upload / list / original / delete")
    plugin.register_tool("waves_manage_panel_image", waves_manage_panel_image, "_tool_panel_image")
