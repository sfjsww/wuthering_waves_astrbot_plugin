"""waves_update_settings - 对标 apps/Setting.js"""
from astrbot.api.event import filter, AstrMessageEvent


class SettingsMixin:
    @filter.llm_tool(name="waves_update_settings")
    async def waves_update_settings(self, event: AstrMessageEvent, setting: str, enabled: bool, threshold: int = None):
        '''更新鸣潮插件用户设置。

        Args:
            setting(string): "auto_sign"/"auto_task"/"sanity_push"/"news_push"
            enabled(bool): 开启或关闭
            threshold(int, optional): 体力推送阈值
        '''
        user_id = event.get_sender_id()
        if setting == "sanity_push" and threshold:
            self.config_mgr.set_config("sanity_threshold", threshold)
        action = "开启" if enabled else "关闭"
        name_map = {"auto_sign": "自动签到", "auto_task": "自动任务", "sanity_push": "体力推送", "news_push": "公告推送"}
        name = name_map.get(setting, setting)
        yield event.plain_result(f"已{action} {name}" + (f"，阈值: {threshold}" if threshold else ""))
