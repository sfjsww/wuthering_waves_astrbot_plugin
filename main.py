"""鸣潮插件 AstrBot 主入口 - 继承 25 个 Mixin 提供 LLM Tools + 4 个后台定时任务"""
import sys
from pathlib import Path

# 将插件目录加入 Python 路径，确保 core/ 和 tools/ 模块可导入
sys.path.insert(0, str(Path(__file__).parent))

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from tools.calendar import CalendarMixin
from tools.news import NewsMixin
from tools.reward import RewardMixin
from tools.emoji import EmojiMixin
from tools.guide import GuideMixin
from tools.strategy import StrategyMixin
from tools.simulate_gacha import SimulateGachaMixin
from tools.help import HelpMixin
from tools.update import UpdateMixin
from tools.character import CharacterMixin
from tools.user_info import UserInfoMixin
from tools.data_dock import DataDockMixin
from tools.challenge import ChallengeMixin
from tools.exploration import ExplorationMixin
from tools.tower import TowerMixin
from tools.training import TrainingMixin
from tools.sanity import SanityMixin
from tools.gacha import GachaMixin
from tools.signin import SigninMixin
from tools.daily_task import DailyTaskMixin
from tools.account import AccountMixin
from tools.settings import SettingsMixin
from tools.alias import AliasMixin
from tools.panel_image import PanelImageMixin
from tools.admin import AdminMixin

RESOURCES_DIR = Path(__file__).parent / "resources"


@register(
    "wuthering_waves_astrbot_plugin",
    "sfjsww",
    "基于库街区的鸣潮游戏数据查询插件，支持角色面板、签到、抽卡记录、数据坞、深塔等全部功能。",
    "1.0.0",
    "https://github.com/sfjsww/wuthering_waves_astrbot_plugin"
)
class WavesPlugin(
    CalendarMixin, NewsMixin, RewardMixin, EmojiMixin,
    GuideMixin, StrategyMixin, SimulateGachaMixin, HelpMixin, UpdateMixin,
    CharacterMixin, UserInfoMixin, DataDockMixin, ChallengeMixin,
    ExplorationMixin, TowerMixin, TrainingMixin, SanityMixin, GachaMixin,
    SigninMixin, DailyTaskMixin, AccountMixin, SettingsMixin, AliasMixin,
    PanelImageMixin, AdminMixin,
    Star,
):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        if config is None:
            config = {}
        self.astrbot_config = config
        self.data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "wuthering_waves_astrbot_plugin"
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

        asyncio.create_task(self.login_server.start())
        self.scheduler = AsyncIOScheduler()
        self._setup_cron_jobs()
        self.scheduler.start()
        logger.info("[Waves] 鸣潮插件初始化完成，25 个 Mixin 已加载")

    def _setup_cron_jobs(self):
        self.scheduler.add_job(self._auto_signin, "cron", hour=0, minute=10, id="waves_auto_signin")
        self.scheduler.add_job(self._auto_task, "cron", hour=6, minute=0, id="waves_auto_task")
        self.scheduler.add_job(self._auto_sanity_push, "cron", hour="*/7", id="waves_sanity_push")
        self.scheduler.add_job(self._auto_news_push, "cron", minute="*/15", id="waves_news_push")

    async def _auto_signin(self):
        """后台自动签到（对标 SignIn.js autoSignIn）"""
        users = self.config_mgr.get_config().get("waves_auto_signin_list", [])
        interval = self.config_mgr.get_config().get("signin_interval", 37)
        success = 0
        for user_entry in users:
            user_id = user_entry.get("userId", "")
            tokens = self.config_mgr.get_user_tokens(user_id)
            for account in tokens:
                ok = await self.kuro.is_available(account["serverId"], account["roleId"], account["token"])
                if not ok:
                    continue
                result = await self.kuro.sign_in(account["serverId"], account["roleId"], account.get("userId", account["roleId"]), account["token"])
                if result["status"]:
                    success += 1
                await asyncio.sleep(interval)
        logger.info(f"[Waves] 自动签到完成，成功 {success} 个账号")

    async def _auto_task(self):
        """后台自动每日任务（对标 Task.js autoTask）"""
        users = self.config_mgr.get_config().get("waves_auto_task_list", [])
        interval = self.config_mgr.get_config().get("task_interval", 37)
        for user_entry in users:
            user_id = user_entry.get("userId", "")
            tokens = self.config_mgr.get_user_tokens(user_id)
            for account in tokens:
                ok = await self.kuro.is_available(account["serverId"], account["roleId"], account["token"])
                if not ok:
                    continue
                await asyncio.sleep(interval)
        logger.info("[Waves] 自动任务完成")

    async def _auto_sanity_push(self):
        """后台体力推送（对标 Sanity.js autoPush）"""
        users = self.config_mgr.get_config().get("waves_auto_push_list", [])
        for user_entry in users:
            user_id = user_entry.get("userId", "")
            tokens = self.config_mgr.get_user_tokens(user_id)
            for account in tokens:
                try:
                    data = await self.kuro.get_game_data(account["token"])
                    if data["status"]:
                        energy = data["data"].get("energyData", {}).get("cur", 0)
                        threshold = self.config_mgr.get_config().get("sanity_threshold", 180)
                        if energy >= threshold:
                            logger.info(f"[Waves] 用户 {user_id} 体力已达 {energy}")
                except Exception:
                    pass

    async def _auto_news_push(self):
        """后台公告推送（对标 News.js autoNews）"""
        try:
            events = await self.kuro.get_event_list()
            if events["status"]:
                logger.info("[Waves] 公告推送检查完成")
        except Exception as e:
            logger.error(f"[Waves] 公告推送错误: {e}")

    async def terminate(self):
        await self.login_server.stop()
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("[Waves] 鸣潮插件已卸载")
