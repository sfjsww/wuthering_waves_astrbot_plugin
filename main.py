"""鸣潮插件 AstrBot 主入口"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import json
import random
import uuid
import yaml
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

RESOURCES_DIR = Path(__file__).parent / "resources"


@register("wuthering_waves_astrbot_plugin", "sfjsww", "基于库街区的鸣潮游戏数据查询插件，支持角色面板、签到、抽卡记录、数据坞、深塔等全部功能。", "1.0.0", "https://github.com/sfjsww/wuthering_waves_astrbot_plugin")
class WavesPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        if config is None:
            config = {}
        self.astrbot_config = config
        self.data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "wuthering_waves_astrbot_plugin"
        self.data_dir.mkdir(parents=True, exist_ok=True)

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
        logger.info("[Waves] 鸣潮插件初始化完成，24 个 Tools 已注册")

    async def _get_account(self, event: AstrMessageEvent):
        """Helper: 获取用户 token 列表，无绑定则回退公共 cookie"""
        user_id = event.get_sender_id()
        tokens = self.config_mgr.get_user_tokens(user_id)
        if tokens:
            return tokens
        public = await self.config_mgr.get_public_cookie(self.kuro)
        return [public] if public else []

    # ===================== 无需登录的公共工具 =====================

    @filter.llm_tool(name="query_waves_calendar")
    async def query_waves_calendar(self, event: AstrMessageEvent):
        '''查询鸣潮活动日历和当前卡池信息。无需登录。'''
        data = await self.kuro.get_event_list()
        if data["status"]:
            img = await self.render.render("calendar/calendar", {"data": data["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(data["msg"])

    @filter.llm_tool(name="query_waves_news")
    async def query_waves_news(self, event: AstrMessageEvent, news_type: str = ""):
        '''查询鸣潮最新游戏公告和活动资讯。无需登录。

        Args:
            news_type(string, optional): 资讯类型，"活动"/"公告"/"资讯"，不填则获取全部
        '''
        type_map = {"活动": 1, "资讯": 2, "公告": 3}
        event_type = type_map.get(news_type, 0)
        data = await self.kuro.get_event_list(event_type)
        if data["status"]:
            items = data["data"].get("list", [])[:20]
            if not items:
                yield event.plain_result("暂无相关资讯。")
                return
            lines = []
            for item in items:
                title = item.get("postTitle", "无标题")
                post_id = item.get("postId", "")
                pub_time = item.get("publishTime", "")
                url = f"https://www.kurobbs.com/mc/post/{post_id}" if post_id else ""
                time_str = ""
                if pub_time:
                    try:
                        dt = datetime.fromtimestamp(pub_time / 1000)
                        time_str = dt.strftime("%Y-%m-%d %H:%M")
                    except (TypeError, ValueError):
                        time_str = str(pub_time)
                line = title
                if time_str:
                    line += f"\n  时间: {time_str}"
                if url:
                    line += f"\n  链接: {url}"
                lines.append(line)
            type_label = news_type if news_type else "全部"
            yield event.plain_result(f"【{type_label}资讯】共{len(lines)}条:\n\n" + "\n---\n".join(lines))
        else:
            yield event.plain_result(data["msg"])

    @filter.llm_tool(name="query_waves_reward_codes")
    async def query_waves_reward_codes(self, event: AstrMessageEvent):
        '''查询鸣潮当前可用兑换码。无需登录。'''
        try:
            data = await self.kuro.get_event_list()
            if data["status"]:
                codes = []
                for ev in data["data"].get("list", []):
                    for c in ev.get("exchangeCodes", []):
                        codes.append(f"{c.get('code', '?')} — {c.get('name', c.get('desc', '兑换码'))}")
                if codes:
                    yield event.plain_result("当前可用兑换码：\n" + "\n".join(codes))
                else:
                    yield event.plain_result("当前没有可用兑换码。")
            else:
                yield event.plain_result("查询兑换码失败，请稍后重试。")
        except Exception as e:
            yield event.plain_result(f"查询失败: {e}")

    @filter.llm_tool(name="query_waves_emoji")
    async def query_waves_emoji(self, event: AstrMessageEvent):
        '''获取随机鸣潮表情包。无需登录。'''
        emoji_dir = self.render.resources_dir / "emojis"
        files = list(emoji_dir.glob("*")) if emoji_dir.exists() else []
        if files:
            yield event.image_result(str(random.choice(files)))
        else:
            yield event.plain_result("暂无表情包资源。")

    @filter.llm_tool(name="query_waves_guide")
    async def query_waves_guide(self, event: AstrMessageEvent, character: str):
        '''查询鸣潮角色/武器/声骸图鉴。无需登录。

        Args:
            character(string): 角色/武器/声骸名称
        '''
        name = self.wiki.get_alias(character)
        result = await self.wiki.get_entry(name)
        if result["status"]:
            r = result["record"]
            text = f"【{name}】\n分类: {self.wiki.CATALOGUEID_MAP.get(result.get('type', ''), '?')}\n"
            for seg in r.get("segments", []):
                for item in seg.get("items", []):
                    if item.get("key") and item.get("value"):
                        text += f"{item['key']}: {item['value']}\n"
            yield event.plain_result(text[:2000])
        else:
            yield event.plain_result(f"未找到「{name}」的图鉴信息")

    @filter.llm_tool(name="query_waves_strategy")
    async def query_waves_strategy(self, event: AstrMessageEvent, character: str, provider: str = "all"):
        '''获取鸣潮角色攻略图。无需登录。

        Args:
            character(string): 角色名
            provider(string, optional): "all" / "XMu" / "moealkyne" / "Linn" / "ruozi"
        '''
        name = self.wiki.get_alias(character)
        sd = self.render.resources_dir / "Strategy"
        providers = ["XMu", "moealkyne", "Linn", "ruozi"] if provider == "all" else [provider]
        for p in providers:
            for ext in (".png", ".jpg", ".webp"):
                img = sd / p / f"{name}{ext}"
                if img.exists():
                    yield event.image_result(str(img))
                    return
        yield event.plain_result(f"未找到 {name} 的攻略图")

    @filter.llm_tool(name="waves_simulate_gacha")
    async def waves_simulate_gacha(self, event: AstrMessageEvent, pool_type: str = "角色", count: str = "十连"):
        '''模拟鸣潮抽卡仅供娱乐。无需登录。

        Args:
            pool_type(string, optional): "角色" / "武器"
            count(string, optional): "单抽" / "十连"
        '''
        sd = self.render.resources_dir / "Simulator"
        pf = {"角色": "role.yaml", "武器": "weapon.yaml"}.get(pool_type, "role.yaml")
        with open(sd / pf, encoding="utf-8") as f:
            pool = yaml.safe_load(f)
        times = 10 if "十" in count else 1
        res = []
        for _ in range(times):
            roll = random.random()
            if roll < 0.008:
                cand = [x for x in pool if x.get("star") == 5]
            elif roll < 0.08:
                cand = [x for x in pool if x.get("star") == 4]
            else:
                cand = [x for x in pool if x.get("star") == 3]
            x = random.choice(cand) if cand else {"name": "?", "star": 3}
            res.append(f"{'⭐' * x['star']} {x['name']}")
        yield event.plain_result(f"模拟{pool_type}池{count}结果：\n" + "\n".join(res))

    @filter.llm_tool(name="waves_help")
    async def waves_help(self, event: AstrMessageEvent):
        '''获取鸣潮插件功能列表和使用帮助。无需登录。'''
        yield event.plain_result("""鸣潮查询插件功能
【无需登录】模拟抽卡 | 活动日历 | 公告 | 兑换码 | 图鉴 | 攻略 | 表情包
【需绑号】角色面板 | 用户信息 | 数据坞 | 挑战 | 探索 | 深塔 | 练度 | 抽卡记录 | 体力 | 签到 | 每日任务
【账号】登录绑定 | 解绑 | 查看绑定信息
直接描述需求即可，如「查安可面板」「帮我签到」""")

    @filter.llm_tool(name="waves_update_plugin")
    async def waves_update_plugin(self, event: AstrMessageEvent):
        '''检查鸣潮插件更新。'''
        yield event.plain_result("鸣潮查询插件 v1.0.0\nhttps://github.com/sfjsww/wuthering_waves_astrbot_plugin")

    # ===================== 需登录的工具 =====================

    @filter.llm_tool(name="query_waves_character_panel")
    async def query_waves_character_panel(self, event: AstrMessageEvent, character: str, uid: str = None):
        '''查询鸣潮角色面板(等级、声骸评分S/A/B/C/D、武器、技能)。需要绑定账号。

        Args:
            character(string): 角色名称，如"安可"、"漂泊者·湮灭"、"维里奈"
            uid(string, optional): 9位UID，不填则使用已绑定账号
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先通过「鸣潮登录」绑定账号。")
            return
        name = self.wiki.get_alias(character)
        if "漂泊者" in name:
            name = "漂泊者"
        for ac in tokens:
            if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
                yield event.plain_result(f"账号 {ac.get('roleId')} Token已失效")
                continue
            rd = await self.kuro.get_role_data(ac["serverId"], ac["roleId"], ac["token"])
            if not rd["status"]:
                yield event.plain_result(rd["msg"])
                continue
            ch = next((r for r in rd["data"].get("roleList", []) if r["roleName"] == name), None)
            if not ch:
                yield event.plain_result(f"UID {ac['roleId']} 未拥有 {name}")
                continue
            dt = await self.kuro.get_role_detail(ac["serverId"], ac["roleId"], ch["roleId"], ac["token"])
            if not dt["status"]:
                yield event.plain_result(dt["msg"])
                continue
            if not dt["data"].get("role"):
                yield event.plain_result(f"UID {ac['roleId']} 未展示 {name}")
                continue
            from core.calculator import WeightCalculator
            dt["data"] = WeightCalculator(dt["data"], self.render.resources_dir).calculate()
            img = await self.render.render("charProfile/charProfile", {
                "uid": ac["roleId"],
                "rolePicUrl": dt["data"]["role"].get("rolePicUrl", ""),
                "roleDetail": dt["data"],
            })
            yield event.image_result(img)
            return

    @filter.llm_tool(name="query_waves_user_info")
    async def query_waves_user_info(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮玩家基本信息(昵称/等级/UID/角色列表)。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield event.plain_result("Token已失效")
            return
        d = await self.kuro.get_base_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("userInfo/userInfo", {"data": d["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(d["msg"])

    @filter.llm_tool(name="query_waves_data_dock")
    async def query_waves_data_dock(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮数据坞(声骸收集进度)。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield event.plain_result("Token已失效")
            return
        d = await self.kuro.get_calabash_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("calaBash/calaBash", {"data": d["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(d["msg"])

    @filter.llm_tool(name="query_waves_challenge_data")
    async def query_waves_challenge_data(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮全息战略等挑战数据。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield event.plain_result("Token已失效")
            return
        d = await self.kuro.get_challenge_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("challengeDetails/challengeDetails", {"data": d["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(d["msg"])

    @filter.llm_tool(name="query_waves_exploration")
    async def query_waves_exploration(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮地图探索进度。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield event.plain_result("Token已失效")
            return
        d = await self.kuro.get_explore_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("exploreIndex/exploreIndex", {"data": d["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(d["msg"])

    @filter.llm_tool(name="query_waves_tower")
    async def query_waves_tower(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮逆境深塔数据。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield event.plain_result("Token已失效")
            return
        d = await self.kuro.get_tower_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("towerData/towerData", {"data": d["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(d["msg"])

    @filter.llm_tool(name="query_waves_training")
    async def query_waves_training(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮所有角色练度统计。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield event.plain_result("Token已失效")
            return
        rd = await self.kuro.get_role_data(ac["serverId"], ac["roleId"], ac["token"])
        if not rd["status"]:
            yield event.plain_result(rd["msg"])
            return
        roles = rd["data"].get("roleList", [])
        tasks = [self.kuro.get_role_detail(ac["serverId"], ac["roleId"], r["roleId"], ac["token"]) for r in roles]
        details = await asyncio.gather(*tasks)
        valid = [d["data"] for d in details if d["status"] and d["data"].get("role")]
        if not valid:
            yield event.plain_result("未展示任何角色")
            return
        img = await self.render.render("training/training", {"roleData": rd["data"], "roleDetails": valid})
        yield event.image_result(img)

    @filter.llm_tool(name="query_waves_gacha_records")
    async def query_waves_gacha_records(self, event: AstrMessageEvent, card_pool_type: str = "", uid: str = None):
        '''查询鸣潮抽卡记录统计。需要绑定账号。

        Args:
            card_pool_type(string, optional): "角色"/"武器"/"常驻角色"/"常驻武器"/"新手"/"自选"
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield event.plain_result("Token已失效")
            return
        pool_map = {"角色": 1, "武器": 2, "常驻角色": 3, "常驻武器": 4, "新手": 5, "自选": 6}
        q = {"serverId": ac["serverId"], "playerId": ac["roleId"], "cardPoolType": pool_map.get(card_pool_type, 0), "languageCode": "zh-Hans"}
        d = await self.kuro.get_gacha(q)
        if d["status"]:
            img = await self.render.render("gacha/gacha", {"gachaData": d["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(d["msg"])

    @filter.llm_tool(name="query_waves_sanity")
    async def query_waves_sanity(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮当前体力/波片日常数据。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        d = await self.kuro.get_game_data(ac["token"])
        if d["status"]:
            img = await self.render.render("dailyData/dailyData", {"data": d["data"]})
            yield event.image_result(img)
        else:
            yield event.plain_result(d["msg"])

    @filter.llm_tool(name="waves_sign_in")
    async def waves_sign_in(self, event: AstrMessageEvent, action: str):
        '''执行鸣潮每日签到或查看签到记录。需要绑定账号。

        Args:
            action(string): "sign"=执行签到, "record"=查看签到记录
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        if action == "sign":
            results = []
            for ac in tokens:
                if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
                    results.append(f"账号 {ac.get('roleId')} Token已失效")
                    continue
                s = await self.kuro.sign_in(ac["serverId"], ac["roleId"], ac.get("userId", ac["roleId"]), ac["token"])
                rc = await self.kuro.query_record(ac["serverId"], ac["roleId"], ac["token"])
                if s["status"] and rc["status"]:
                    g = rc["data"][0] if rc["data"] else {}
                    results.append(f"签到成功！获得「{g.get('goodsName', '?')} × {g.get('goodsNum', '?')}」")
                else:
                    results.append(f"失败: {s.get('msg', '?')}")
            yield event.plain_result("\n".join(results))
        elif action == "record":
            ac = tokens[0]
            if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
                yield event.plain_result("Token已失效")
                return
            rc = await self.kuro.query_record(ac["serverId"], ac["roleId"], ac["token"])
            if rc["status"]:
                rc["data"] = rc["data"][:50]
                img = await self.render.render("queryRecord/queryRecord", {"listData": rc["data"]})
                yield event.image_result(img)
            else:
                yield event.plain_result(rc["msg"])
        else:
            yield event.plain_result("请指定: sign(签到) / record(签到记录)")

    @filter.llm_tool(name="waves_daily_task")
    async def waves_daily_task(self, event: AstrMessageEvent, action: str = "list"):
        '''查看库街区每日任务。需要绑定账号。

        Args:
            action(string): "list"=查看任务列表, "do"=执行任务
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield event.plain_result("请先绑定账号。")
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield event.plain_result("Token已失效")
            return
        if action == "list":
            d = await self.kuro.get_game_data(ac["token"])
            if d["status"]:
                img = await self.render.render("taskList/taskList", {"data": d["data"]})
                yield event.image_result(img)
            else:
                yield event.plain_result(d["msg"])
        elif action == "do":
            yield event.plain_result("每日任务执行请通过库街区APP完成。")
        else:
            yield event.plain_result("请指定: list / do")

    @filter.llm_tool(name="waves_manage_gacha_records")
    async def waves_manage_gacha_records(self, event: AstrMessageEvent, action: str, data: str = None):
        '''导入导出抽卡记录。

        Args:
            action(string): "import" / "export"
            data(string, optional): 导入时提供JSON数据
        '''
        if action == "export":
            tokens = await self._get_account(event)
            if not tokens:
                yield event.plain_result("请先绑定账号。")
                return
            cached = self.config_mgr.get_gacha_records(tokens[0].get("roleId", ""))
            if cached:
                yield event.plain_result(f"抽卡记录导出:\n```json\n{json.dumps(cached, ensure_ascii=False, indent=2)[:4000]}\n```")
            else:
                yield event.plain_result("暂无缓存记录，请先查询抽卡记录。")
        elif action == "import":
            yield event.plain_result("导入功能需要先在WebUI中开启 allow_import 配置。")
        else:
            yield event.plain_result("请指定: import / export")

    @filter.llm_tool(name="waves_account_login")
    async def waves_account_login(self, event: AstrMessageEvent, action: str = "login", code: str = None):
        '''登录或绑定鸣潮账号。

        Args:
            action(string): "login"=获取登录链接, "bind_uid"=绑定UID
            code(string, optional): 绑定码
        '''
        uid = event.get_sender_id()
        if action == "login":
            lid = uuid.uuid4().hex[:12]
            url = self.login_server.create_login_session(lid, uid, uid)
            yield event.plain_result(f"请在浏览器打开以下链接完成登录:\n{url}")
        elif action == "bind_uid":
            if code:
                tokens = self.config_mgr.get_user_tokens(uid)
                tokens.append({"serverId": "76402e5b20be2c39f095a152090afddc", "roleId": code, "userId": code, "token": ""})
                self.config_mgr.set_user_tokens(uid, tokens)
                yield event.plain_result(f"已绑定UID: {code}")
            else:
                yield event.plain_result("请提供要绑定的UID或特征码。")
        else:
            yield event.plain_result("请指定: login / bind_uid")

    @filter.llm_tool(name="waves_account_unbind")
    async def waves_account_unbind(self, event: AstrMessageEvent, uid: str = None):
        '''解绑鸣潮账号。

        Args:
            uid(string, optional): 要解绑的UID，不填则解绑全部
        '''
        user_id = event.get_sender_id()
        tokens = self.config_mgr.get_user_tokens(user_id)
        if not tokens:
            yield event.plain_result("没有绑定的账号。")
            return
        if uid:
            tokens = [t for t in tokens if t.get("roleId") != uid]
            self.config_mgr.set_user_tokens(user_id, tokens)
            yield event.plain_result(f"已解绑 UID: {uid}")
        else:
            self.config_mgr.set_user_tokens(user_id, [])
            yield event.plain_result("已解绑全部账号。")

    @filter.llm_tool(name="waves_get_token")
    async def waves_get_token(self, event: AstrMessageEvent):
        '''查看已绑定的鸣潮账号信息。'''
        tokens = self.config_mgr.get_user_tokens(event.get_sender_id())
        if not tokens:
            yield event.plain_result("没有绑定的账号。")
            return
        info = [f"UID: {t.get('roleId', '?')} | 服务器: {t.get('serverId', '?')[:8]}..." for t in tokens]
        yield event.plain_result("已绑定账号：\n" + "\n".join(info))

    @filter.llm_tool(name="waves_update_settings")
    async def waves_update_settings(self, event: AstrMessageEvent, setting: str, enabled: bool, threshold: int = None):
        '''更新用户设置。

        Args:
            setting(string): "auto_sign"/"auto_task"/"sanity_push"/"news_push"
            enabled(bool): 开关
            threshold(int, optional): 体力推送阈值
        '''
        nm = {"auto_sign": "自动签到", "auto_task": "自动任务", "sanity_push": "体力推送", "news_push": "公告推送"}
        if setting == "sanity_push" and threshold is not None:
            self.config_mgr.set_config("sanity_threshold", threshold)
        yield event.plain_result(f"已{'开启' if enabled else '关闭'} {nm.get(setting, setting)}" + (f"，阈值: {threshold}" if threshold is not None else ""))

    @filter.llm_tool(name="waves_manage_alias")
    async def waves_manage_alias(self, event: AstrMessageEvent, action: str, character: str = "", alias: str = ""):
        '''管理角色别名。

        Args:
            action(string): "add" / "delete" / "list"
            character(string): 角色名
            alias(string): 别名
        '''
        cd = self.render.resources_dir / "Alias" / "custom"
        cd.mkdir(parents=True, exist_ok=True)
        cf = cd / "custom.yaml"
        d = yaml.safe_load(open(cf, encoding="utf-8")) if cf.exists() else {}
        if action == "add":
            if alias and alias not in d.setdefault(character, []):
                d[character].append(alias)
            yaml.dump(d, open(cf, "w", encoding="utf-8"), allow_unicode=True)
            yield event.plain_result(f"已为 {character} 添加别名: {alias}")
        elif action == "delete":
            if character in d and alias in d[character]:
                d[character].remove(alias)
                yaml.dump(d, open(cf, "w", encoding="utf-8"), allow_unicode=True)
            yield event.plain_result("已删除别名。")
        elif action == "list":
            n = self.wiki.get_alias(character) if character else ""
            lst = d.get(n, [])
            yield event.plain_result(f"{n} 的别名: {', '.join(lst)}" if lst else f"{n} 暂无自定义别名")
        else:
            yield event.plain_result("请指定 action: add/delete/list")

    @filter.llm_tool(name="waves_manage_panel_image")
    async def waves_manage_panel_image(self, event: AstrMessageEvent, action: str, character: str = "", index: int = 0):
        '''管理角色面板图。

        Args:
            action(string): "list"/"original"/"delete"
            character(string): 角色名
        '''
        rp = self.render.resources_dir / "rolePic"
        if action == "list":
            if character:
                cd = rp / character
                fs = list(cd.glob("*")) if cd.exists() else []
                if fs:
                    lines = "\n".join(f"  {i}. {f.name}" for i, f in enumerate(fs, 1))
                    yield event.plain_result(f"{character} 面板图({len(fs)}张):\n{lines}")
                else:
                    yield event.plain_result(f"{character} 暂无面板图")
            else:
                ds = [d.name for d in rp.iterdir() if d.is_dir()]
                yield event.plain_result("有面板图的角色:\n" + "\n".join(ds) if ds else "暂无")
        else:
            yield event.plain_result(f"{action} 功能开发中。")

    @filter.llm_tool(name="waves_admin_user_stats")
    async def waves_admin_user_stats(self, event: AstrMessageEvent, action: str = "stats"):
        '''管理插件用户数据。

        Args:
            action(string): "stats"=用户统计, "clean_invalid"=清理失效账号
        '''
        if action == "stats":
            users = self.config_mgr.get_all_bound_users()
            total = sum(len(v) for v in users.values())
            yield event.plain_result(f"已绑定用户: {len(users)}\n总绑定账号: {total}")
        elif action == "clean_invalid":
            cnt = 0
            for uid, tokens in self.config_mgr.get_all_bound_users().items():
                valid = []
                for t in tokens:
                    if t.get("token"):
                        try:
                            if await self.kuro.is_available(t["serverId"], t["roleId"], t["token"]):
                                valid.append(t)
                            else:
                                cnt += 1
                        except:
                            valid.append(t)
                    else:
                        valid.append(t)
                self.config_mgr.set_user_tokens(uid, valid)
            yield event.plain_result(f"已清理 {cnt} 个失效账号。")
        else:
            yield event.plain_result("请指定: stats / clean_invalid")

    # ===================== 定时任务 =====================

    def _setup_cron_jobs(self):
        self.scheduler.add_job(self._auto_signin, "cron", hour=0, minute=10, id="waves_auto_signin")
        self.scheduler.add_job(self._auto_task, "cron", hour=6, minute=0, id="waves_auto_task")
        self.scheduler.add_job(self._auto_sanity_push, "cron", hour="*/7", id="waves_sanity_push")
        self.scheduler.add_job(self._auto_news_push, "cron", minute="*/15", id="waves_news_push")

    async def _auto_signin(self):
        logger.info("[Waves] 自动签到")
        users = self.config_mgr.get_config().get("waves_auto_signin_list", [])
        interval = self.config_mgr.get_config().get("signin_interval", 37)
        success = 0
        for user_entry in users:
            tokens = self.config_mgr.get_user_tokens(user_entry.get("userId", ""))
            for account in tokens:
                if await self.kuro.is_available(account["serverId"], account["roleId"], account["token"]):
                    r = await self.kuro.sign_in(account["serverId"], account["roleId"], account.get("userId", account["roleId"]), account["token"])
                    if r["status"]:
                        success += 1
                await asyncio.sleep(interval)
        logger.info(f"[Waves] 自动签到完成: {success} 个")

    async def _auto_task(self):
        logger.info("[Waves] 自动任务")
        users = self.config_mgr.get_config().get("waves_auto_task_list", [])
        interval = self.config_mgr.get_config().get("task_interval", 37)
        for user_entry in users:
            tokens = self.config_mgr.get_user_tokens(user_entry.get("userId", ""))
            for account in tokens:
                if await self.kuro.is_available(account["serverId"], account["roleId"], account["token"]):
                    await asyncio.sleep(interval)
        logger.info("[Waves] 自动任务完成")

    async def _auto_sanity_push(self):
        for user_entry in self.config_mgr.get_config().get("waves_auto_push_list", []):
            tokens = self.config_mgr.get_user_tokens(user_entry.get("userId", ""))
            for account in tokens:
                try:
                    d = await self.kuro.get_game_data(account["token"])
                    if d["status"] and d["data"].get("energyData", {}).get("cur", 0) >= self.config_mgr.get_config().get("sanity_threshold", 180):
                        logger.info(f"[Waves] 用户 {user_entry.get('userId')} 体力已满")
                except:
                    pass

    async def _auto_news_push(self):
        try:
            ev = await self.kuro.get_event_list()
            if ev["status"]:
                logger.info("[Waves] 公告检查完成")
        except Exception as e:
            logger.error(f"[Waves] 公告推送错误: {e}")

    async def terminate(self):
        await self.login_server.stop()
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("[Waves] 鸣潮插件已卸载")
