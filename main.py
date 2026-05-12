"""鸣潮插件 AstrBot 主入口 - 注册 24 个 LLM Tools + 4 个后台定时任务"""
import asyncio
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

RESOURCES_DIR = Path(__file__).parent / "resources"


@register(
    "wuthering_waves_astrbot_plugin",
    "sfjsww",
    "基于库街区的鸣潮游戏数据查询插件，支持角色面板、签到、抽卡记录、数据坞、深塔等全部功能。",
    "1.0.0",
    "https://github.com/sfjsww/wuthering_waves_astrbot_plugin"
)
class WavesPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.astrbot_config = config
        self.data_dir = get_astrbot_data_path() / "plugin_data" / "wuthering_waves_astrbot_plugin"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Defer imports to avoid import errors before AstrBot is fully loaded
        from core.config_mgr import ConfigManager
        from core.kuro_api import KuroApi
        from core.wiki import Wiki
        from core.render import Render
        from core.login_server import LoginServer

        self.config_mgr = ConfigManager(config, self.data_dir)
        self.kuro = KuroApi(self.config_mgr, logger)
        self.wiki = Wiki(RESOURCES_DIR, self.kuro, logger)
        self.render = Render(RESOURCES_DIR, self.config_mgr)
        self.login_server = LoginServer(self.config_mgr, self.kuro, RESOURCES_DIR, logger)

        self._register_all_tools()

        asyncio.create_task(self.login_server.start())
        self.scheduler = AsyncIOScheduler()
        self._setup_cron_jobs()
        self.scheduler.start()
        logger.info("[Waves] 鸣潮插件初始化完成，24 个 Tools 已注册")

    def _register_all_tools(self):
        from tools.character import register_character_tool
        from tools.user_info import register_user_info_tool
        from tools.data_dock import register_data_dock_tool
        from tools.challenge import register_challenge_tool
        from tools.exploration import register_exploration_tool
        from tools.tower import register_tower_tool
        from tools.training import register_training_tool
        from tools.gacha import register_gacha_tools
        from tools.sanity import register_sanity_tool
        from tools.guide import register_guide_tool
        from tools.strategy import register_strategy_tool
        from tools.calendar import register_calendar_tool
        from tools.news import register_news_tool
        from tools.reward import register_reward_tool
        from tools.emoji import register_emoji_tool
        from tools.signin import register_signin_tool
        from tools.daily_task import register_daily_task_tool
        from tools.simulate_gacha import register_simulate_gacha_tool
        from tools.account import register_account_tools
        from tools.settings import register_settings_tool
        from tools.alias import register_alias_tool
        from tools.panel_image import register_panel_image_tool
        from tools.admin import register_admin_tool
        from tools.help import register_help_tool
        from tools.update import register_update_tool

        register_character_tool(self)
        register_user_info_tool(self)
        register_data_dock_tool(self)
        register_challenge_tool(self)
        register_exploration_tool(self)
        register_tower_tool(self)
        register_training_tool(self)
        register_gacha_tools(self)
        register_sanity_tool(self)
        register_guide_tool(self)
        register_strategy_tool(self)
        register_calendar_tool(self)
        register_news_tool(self)
        register_reward_tool(self)
        register_emoji_tool(self)
        register_signin_tool(self)
        register_daily_task_tool(self)
        register_simulate_gacha_tool(self)
        register_account_tools(self)
        register_settings_tool(self)
        register_alias_tool(self)
        register_panel_image_tool(self)
        register_admin_tool(self)
        register_help_tool(self)
        register_update_tool(self)

    def _setup_cron_jobs(self):
        self.scheduler.add_job(self._auto_signin, "cron", hour=0, minute=10, id="waves_auto_signin")
        self.scheduler.add_job(self._auto_task, "cron", hour=6, minute=0, id="waves_auto_task")
        self.scheduler.add_job(self._auto_sanity_push, "cron", hour="*/7", id="waves_sanity_push")
        self.scheduler.add_job(self._auto_news_push, "cron", minute="*/15", id="waves_news_push")

    async def _auto_signin(self):
        logger.info("[Waves] 开始执行自动签到")

    async def _auto_task(self):
        pass

    async def _auto_sanity_push(self):
        pass

    async def _auto_news_push(self):
        pass

    async def terminate(self):
        await self.login_server.stop()
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("[Waves] 鸣潮插件已卸载")

    def register_tool(self, tool_name: str, handler, method_name: str):
        """通过装饰器方式注册单个 LLM Tool"""
        decorator = filter.llm_tool(name=tool_name)(handler)
        setattr(self, method_name, decorator.__get__(self, type(self)))
