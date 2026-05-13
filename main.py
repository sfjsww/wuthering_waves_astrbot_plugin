"""鸣潮插件 AstrBot 主入口"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import json
import os
import random
import re
import uuid
import yaml
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import aiohttp

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
            img = await self.render.render("calendar", {"data": data["data"]})
            yield event.image_result(img)
        else:
            yield data["msg"]

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
                yield "暂无相关资讯。"
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
            yield f"【{type_label}资讯】共{len(lines)}条:\n\n" + "\n---\n".join(lines)
        else:
            yield data["msg"]

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
                    yield "当前可用兑换码：\n" + "\n".join(codes)
                else:
                    yield "当前没有可用兑换码。"
            else:
                yield "查询兑换码失败，请稍后重试。"
        except Exception as e:
            yield f"查询失败: {e}"

    @filter.llm_tool(name="query_waves_emoji")
    async def query_waves_emoji(self, event: AstrMessageEvent):
        '''获取随机鸣潮表情包。无需登录。'''
        emoji_dir = self.render.resources_dir / "emojis"
        files = list(emoji_dir.glob("*")) if emoji_dir.exists() else []
        if files:
            yield event.image_result(str(random.choice(files)))
        else:
            yield "暂无表情包资源。"

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
            yield text[:2000]
        else:
            yield f"未找到「{name}」的图鉴信息"

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
        yield f"未找到 {name} 的攻略图"

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
        yield f"模拟{pool_type}池{count}结果：\n" + "\n".join(res)

    @filter.llm_tool(name="waves_help")
    async def waves_help(self, event: AstrMessageEvent):
        '''获取鸣潮插件功能列表和使用帮助。无需登录。'''
        yield """鸣潮查询插件功能
【无需登录】模拟抽卡 | 活动日历 | 公告 | 兑换码 | 图鉴 | 攻略 | 表情包
【需绑号】角色面板 | 用户信息 | 数据坞 | 挑战 | 探索 | 深塔 | 练度 | 抽卡记录 | 体力 | 签到 | 每日任务
【账号】登录绑定 | 解绑 | 查看绑定信息
直接描述需求即可，如「查安可面板」「帮我签到」"""

    @filter.llm_tool(name="waves_update_plugin")
    async def waves_update_plugin(self, event: AstrMessageEvent):
        '''检查鸣潮插件更新。'''
        yield "鸣潮查询插件 v1.0.0\nhttps://github.com/sfjsww/wuthering_waves_astrbot_plugin"

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
            yield "请先通过「鸣潮登录」绑定账号。"
            return
        name = self.wiki.get_alias(character)
        if "漂泊者" in name:
            name = "漂泊者"
        for ac in tokens:
            if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
                yield f"账号 {ac.get('roleId')} Token已失效"
                continue
            rd = await self.kuro.get_role_data(ac["serverId"], ac["roleId"], ac["token"])
            if not rd["status"]:
                yield rd["msg"]
                continue
            ch = next((r for r in rd["data"].get("roleList", []) if r["roleName"] == name), None)
            if not ch:
                yield f"UID {ac['roleId']} 未拥有 {name}"
                continue
            dt = await self.kuro.get_role_detail(ac["serverId"], ac["roleId"], ch["roleId"], ac["token"])
            if not dt["status"]:
                yield dt["msg"]
                continue
            if not dt["data"].get("role"):
                yield f"UID {ac['roleId']} 未展示 {name}"
                continue
            from core.calculator import WeightCalculator
            dt["data"] = WeightCalculator(dt["data"], self.render.resources_dir).calculate()
            img = await self.render.render("charProfile", {"data": {
                "uid": ac["roleId"],
                "rolePicUrl": dt["data"]["role"].get("rolePicUrl", ""),
                "roleDetail": {"data": dt["data"]},
            }})
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
            yield "请先绑定账号。"
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield "Token已失效"
            return
        d = await self.kuro.get_base_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("userInfo", {"baseData": d["data"]})
            yield event.image_result(img)
        else:
            yield d["msg"]

    @filter.llm_tool(name="query_waves_data_dock")
    async def query_waves_data_dock(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮数据坞(声骸收集进度)。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号。"
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield "Token已失效"
            return
        d = await self.kuro.get_calabash_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("calaBash", {"calabashData": d["data"]})
            yield event.image_result(img)
        else:
            yield d["msg"]

    @filter.llm_tool(name="query_waves_challenge_data")
    async def query_waves_challenge_data(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮全息战略等挑战数据。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号。"
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield "Token已失效"
            return
        d = await self.kuro.get_challenge_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("challengeDetails", {"challengeData": d["data"]})
            yield event.image_result(img)
        else:
            yield d["msg"]

    @filter.llm_tool(name="query_waves_exploration")
    async def query_waves_exploration(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮地图探索进度。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号。"
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield "Token已失效"
            return
        d = await self.kuro.get_explore_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("exploreIndex", {"exploreData": d["data"]})
            yield event.image_result(img)
        else:
            yield d["msg"]

    @filter.llm_tool(name="query_waves_tower")
    async def query_waves_tower(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮逆境深塔数据。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号。"
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield "Token已失效"
            return
        d = await self.kuro.get_tower_data(ac["serverId"], ac["roleId"], ac["token"])
        if d["status"]:
            img = await self.render.render("towerData", {"towerData": d["data"]})
            yield event.image_result(img)
        else:
            yield d["msg"]

    @filter.llm_tool(name="query_waves_training")
    async def query_waves_training(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮所有角色练度统计。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号。"
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield "Token已失效"
            return
        rd = await self.kuro.get_role_data(ac["serverId"], ac["roleId"], ac["token"])
        if not rd["status"]:
            yield rd["msg"]
            return
        roles = rd["data"].get("roleList", [])
        tasks = [self.kuro.get_role_detail(ac["serverId"], ac["roleId"], r["roleId"], ac["token"]) for r in roles]
        details = await asyncio.gather(*tasks)
        valid = [d["data"] for d in details if d["status"] and d["data"].get("role")]
        if not valid:
            yield "未展示任何角色"
            return
        role_list = []
        for r in rd["data"].get("roleList", []):
            detail = next((d for d in valid if d["role"]["roleId"] == r["roleId"]), None)
            merged = dict(r)
            if detail:
                merged.update(detail)
            role_list.append(merged)
        img = await self.render.render("training", {"roleList": role_list, "baseData": rd["data"]})
        yield event.image_result(img)

    @filter.llm_tool(name="query_waves_gacha_records")
    async def query_waves_gacha_records(self, event: AstrMessageEvent, card_pool_type: str = "", uid: str = None):
        '''查询鸣潮抽卡记录统计。优先从缓存读取，无缓存时引导用户导入。

        Args:
            card_pool_type(string, optional): "角色"/"武器"/"常驻角色"/"常驻武器"/"新手"/"自选"
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号，然后使用「导入抽卡记录」导入数据。"
            return
        ac = tokens[0]
        query_uid = uid or ac.get("roleId", "")
        cached = self.config_mgr.get_gacha_records(query_uid)

        if not cached:
            yield f"尚未导入抽卡记录(UID: {query_uid})。请发送 Client.log 文件，然后使用「导入抽卡记录」功能。Client.log 路径: <游戏目录>\\Wuthering Waves\\Wuthering Waves Game\\Client\\Saved\\Logs\\Client.log"
            return

        all_records = cached.get("list", [])
        if not all_records:
            yield "暂无抽卡记录。"
            return

        pool_render_map = {1: "upCharPool", 2: "upWpnPool", 3: "stdCharPool", 4: "stdWpnPool", 5: "otherPool", 6: "upCharPool", 7: "otherPool"}
        pool_reverse = {"角色": 1, "武器": 2, "常驻角色": 3, "常驻武器": 4, "新手": 5, "自选": 6}

        if card_pool_type:
            tid = pool_reverse.get(card_pool_type, 0)
            if tid:
                all_records = [r for r in all_records if r.get("gacha_id") == tid]

        gd = {"playerId": str(query_uid)}
        total = 0
        for gid in {r["gacha_id"] for r in all_records}:
            recs = [r for r in all_records if r["gacha_id"] == gid]
            pid = pool_render_map.get(gid, "otherPool")
            gd.setdefault(pid, []).extend(recs)
        for k in list(gd.keys()):
            if k == "playerId": continue
            fmt = await self._format_gacha_pool(gd[k])
            total += fmt["info"]["total"]
            gd[k] = fmt

        yield f"抽卡记录: 共{total}抽"
        try:
            img = await self.render.render("gacha", {"data": gd})
            yield event.image_result(img)
        except Exception:
            lines = []
            for pk in ["upCharPool", "upWpnPool", "stdCharPool", "stdWpnPool", "otherPool"]:
                pd = gd.get(pk)
                if pd and isinstance(pd, dict) and pd.get("info", {}).get("total", 0) > 0:
                    pl = {"upCharPool": "角色活动", "upWpnPool": "武器活动", "stdCharPool": "常驻角色", "stdWpnPool": "常驻武器", "otherPool": "其他"}.get(pk, pk)
                    lines.append(f"{pl}: {pd['info']['total']}抽")
            yield "\n".join(lines)

    @filter.llm_tool(name="query_waves_sanity")
    async def query_waves_sanity(self, event: AstrMessageEvent, uid: str = None):
        '''查询鸣潮当前体力/波片日常数据。需要绑定账号。

        Args:
            uid(string, optional): 9位UID
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号。"
            return
        ac = tokens[0]
        d = await self.kuro.get_game_data(ac["token"])
        if d["status"]:
            img = await self.render.render("dailyData", {"gameData": d["data"]})
            yield event.image_result(img)
        else:
            yield d["msg"]

    @filter.llm_tool(name="waves_sign_in")
    async def waves_sign_in(self, event: AstrMessageEvent, action: str):
        '''执行鸣潮每日签到或查看签到记录。需要绑定账号。

        Args:
            action(string): "sign"=执行签到, "record"=查看签到记录
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号。"
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
            yield "\n".join(results)
        elif action == "record":
            ac = tokens[0]
            if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
                yield "Token已失效"
                return
            rc = await self.kuro.query_record(ac["serverId"], ac["roleId"], ac["token"])
            if rc["status"]:
                rc["data"] = rc["data"][:50]
                img = await self.render.render("queryRecord", {"data": {"listData": rc["data"]}})
                yield event.image_result(img)
            else:
                yield rc["msg"]
        else:
            yield "请指定: sign(签到) / record(签到记录)"

    @filter.llm_tool(name="waves_daily_task")
    async def waves_daily_task(self, event: AstrMessageEvent, action: str = "list"):
        '''查看库街区每日任务。需要绑定账号。

        Args:
            action(string): "list"=查看任务列表, "do"=执行任务
        '''
        tokens = await self._get_account(event)
        if not tokens:
            yield "请先绑定账号。"
            return
        ac = tokens[0]
        if not await self.kuro.is_available(ac["serverId"], ac["roleId"], ac["token"]):
            yield "Token已失效"
            return
        if action == "list":
            d = await self.kuro.get_game_data(ac["token"])
            if d["status"]:
                img = await self.render.render("taskList", d["data"])
                yield event.image_result(img)
            else:
                yield d["msg"]
        elif action == "do":
            yield "每日任务执行请通过库街区APP完成。"
        else:
            yield "请指定: list / do"

    @filter.llm_tool(name="waves_manage_gacha_records")
    async def waves_manage_gacha_records(self, event: AstrMessageEvent, action: str, data: str = None):
        '''导入导出抽卡记录。导入时若不提供data，会自动尝试从聊天记录中获取用户发送的Client.log文件。

        Args:
            action(string): "import" / "export"
            data(string, optional): 导入时提供URL/JSON/Client.log内容/查询参数，留空则自动获取文件
        '''
        if action == "export":
            tokens = await self._get_account(event)
            if not tokens:
                yield "请先绑定账号。"
                return
            cached = self.config_mgr.get_gacha_records(tokens[0].get("roleId", ""))
            if cached:
                yield f"抽卡记录导出:\n```json\n{json.dumps(cached, ensure_ascii=False, indent=2)[:4000]}\n```"
            else:
                yield "暂无缓存记录，请先导入抽卡记录。"
        elif action == "import":
            if not data:
                # 自动从聊天记录抓文件
                file_result = await self.get_qq_file_content(event)
                if file_result and file_result.startswith("player_id="):
                    data = file_result
                    yield f"已从聊天记录获取抽卡参数: UID={data.split('&')[0].split('=')[1]}"
                else:
                    yield file_result
                    return
            result = await self._do_import_gacha(event, data)
            yield result
        else:
            yield "请指定: import / export"

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
            yield f"请在浏览器打开以下链接完成登录:\n{url}"
        elif action == "bind_uid":
            if code:
                tokens = self.config_mgr.get_user_tokens(uid)
                # 优先更新已有 token 但 roleId 不对的条目（登录后自动保存的情况）
                updated = False
                for t in tokens:
                    if t.get("token") and t.get("roleId") != code:
                        t["roleId"] = code
                        updated = True
                        break
                if not updated:
                    # 没有可更新的条目，新增一个（无token）
                    tokens.append({"serverId": "76402e5b20be2c39f095a152090afddc", "roleId": code, "userId": code, "token": ""})
                self.config_mgr.set_user_tokens(uid, tokens)
                yield f"已绑定游戏UID: {code}"
            else:
                yield "请提供你的9位游戏UID。在游戏内点击左上角头像即可查看。"
        else:
            yield "请指定: login / bind_uid"

    @filter.llm_tool(name="waves_account_unbind")
    async def waves_account_unbind(self, event: AstrMessageEvent, uid: str = None):
        '''解绑鸣潮账号。

        Args:
            uid(string, optional): 要解绑的UID，不填则解绑全部
        '''
        user_id = event.get_sender_id()
        tokens = self.config_mgr.get_user_tokens(user_id)
        if not tokens:
            yield "没有绑定的账号。"
            return
        if uid:
            tokens = [t for t in tokens if t.get("roleId") != uid]
            self.config_mgr.set_user_tokens(user_id, tokens)
            yield f"已解绑 UID: {uid}"
        else:
            self.config_mgr.set_user_tokens(user_id, [])
            yield "已解绑全部账号。"

    @filter.llm_tool(name="waves_get_token")
    async def waves_get_token(self, event: AstrMessageEvent):
        '''查看已绑定的鸣潮账号信息（不包含Token明文）。'''
        tokens = self.config_mgr.get_user_tokens(event.get_sender_id())
        if not tokens:
            yield "当前没有绑定任何鸣潮账号。请先使用「登录」功能绑定账号。"
            return
        lines = []
        for i, t in enumerate(tokens, 1):
            has_token = "✅ 已登录" if t.get("token") else "❌ 未登录"
            lines.append(f"账号{i}: UID={t.get('roleId','?')} 库街区ID={t.get('userId','?')} {has_token}")
        yield "已绑定的鸣潮账号：\n" + "\n".join(lines)

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
        yield f"已{'开启' if enabled else '关闭'} {nm.get(setting, setting)}" + (f"，阈值: {threshold}" if threshold is not None else "")

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
            yield f"已为 {character} 添加别名: {alias}"
        elif action == "delete":
            if character in d and alias in d[character]:
                d[character].remove(alias)
                yaml.dump(d, open(cf, "w", encoding="utf-8"), allow_unicode=True)
            yield "已删除别名。"
        elif action == "list":
            n = self.wiki.get_alias(character) if character else ""
            lst = d.get(n, [])
            yield f"{n} 的别名: {', '.join(lst)}" if lst else f"{n} 暂无自定义别名"
        else:
            yield "请指定 action: add/delete/list"

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
                    yield f"{character} 面板图({len(fs)}张):\n{lines}"
                else:
                    yield f"{character} 暂无面板图"
            else:
                ds = [d.name for d in rp.iterdir() if d.is_dir()]
                yield "有面板图的角色:\n" + "\n".join(ds) if ds else "暂无"
        else:
            yield f"{action} 功能开发中。"

    @filter.llm_tool(name="waves_admin_user_stats")
    async def waves_admin_user_stats(self, event: AstrMessageEvent, action: str = "stats"):
        '''管理插件用户数据。

        Args:
            action(string): "stats"=用户统计, "clean_invalid"=清理失效账号
        '''
        if action == "stats":
            users = self.config_mgr.get_all_bound_users()
            total = sum(len(v) for v in users.values())
            yield f"已绑定用户: {len(users)}\n总绑定账号: {total}"
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
            yield f"已清理 {cnt} 个失效账号。"
        else:
            yield "请指定: stats / clean_invalid"

    # ===================== 文件获取 + 抽卡导入 =====================

    @filter.llm_tool(name="get_qq_file_content")
    async def get_qq_file_content(self, event: AstrMessageEvent) -> str:
        """当用户发送了QQ文件但你收不到内容时调用此工具。它会从聊天记录中找到用户最近发送的文件，通过QQ协议下载并返回文件文本内容。"""
        user_id = event.get_sender_id()
        session_id = event.get_session_id()

        # 搜索群聊和私聊历史
        chat_files = []
        gid = event.get_group_id()
        base = Path("/AstrBot/data/chat_history/aiocqhttp")
        if gid:
            chat_files.append(base / "group" / f"{gid}.json")
        chat_files.append(base / "private" / f"{session_id}.json")

        file_msg = None
        for cf in chat_files:
            if not cf.exists():
                continue
            try:
                with open(cf, encoding="utf-8") as f:
                    msgs = json.load(f)
            except Exception:
                continue
            if not isinstance(msgs, list):
                continue
            for msg in reversed(msgs):
                if msg.get("sender", {}).get("user_id") != user_id:
                    continue
                for comp in msg.get("message", []):
                    ot = comp.get("py/object", "")
                    if "File" in ot:
                        s = comp.get("py/state", {}).get("__dict__", {})
                        file_msg = {"name": s.get("name", ""), "url": s.get("url", ""), "mid": msg.get("message_id", "")}
                        break
                    if "Reply" in ot:
                        for sub in comp.get("py/state", {}).get("__dict__", {}).get("chain", []):
                            if "File" in sub.get("py/object", ""):
                                ss = sub.get("py/state", {}).get("__dict__", {})
                                file_msg = {"name": ss.get("name", ""), "url": ss.get("url", ""), "mid": msg.get("message_id", "")}
                                break
                if file_msg:
                    break
            if file_msg:
                break

        if not file_msg or not file_msg.get("url"):
            return "在聊天记录中未找到你发送的文件。请直接复制Client.log内容并使用「导入抽卡记录」功能。"

        file_url = file_msg["url"]
        content = None

        # 1) 通过平台适配器刷新URL并下载
        try:
            platform = self.context.get_platform_inst("aiocqhttp")
            if platform:
                client = platform.get_client()
                file_id = ""
                mid = file_msg.get("mid", "")
                if mid:
                    try:
                        raw = await client.call_action(action="get_msg", message_id=int(mid))
                        for seg in (raw.get("message") or []):
                            if seg.get("type") == "file":
                                file_id = seg.get("data", {}).get("file_id", "")
                    except Exception:
                        pass
                if file_id:
                    act = "get_group_file_url" if gid else "get_private_file_url"
                    kw = {"file_id": file_id}
                    if gid:
                        kw["group_id"] = int(gid)
                    ret = await client.call_action(action=act, **kw)
                    if ret and "url" in ret:
                        file_url = ret["url"]
        except Exception:
            pass

        # 2) 下载文件
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(file_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        content = await resp.text()
        except Exception:
            pass

        if not content:
            return "无法下载文件(QQ文件链接已过期)。请打开文件全选复制(Ctrl+A→Ctrl+C)，发送「导入抽卡记录」并粘贴内容。"

        # 3) 如果是Client.log，尝试提取gacha参数
        player_id = record_id = server_id = None
        for line in content.split("\n"):
            if "OpenWebView" not in line or "player_id" not in line:
                continue
            m = re.search(r'https?://[^\s"]+', line)
            if not m:
                continue
            url = m.group(0).rstrip('"')
            p = urlparse(url)
            qs = (p.fragment or p.query)
            params = parse_qs(qs.split("?", 1)[1]) if "?" in qs else {}
            pid = params.get("player_id", [None])[0]
            rid = params.get("record_id", [None])[0]
            svr = params.get("svr_id", [None])[0]
            if pid and rid:
                player_id, record_id, server_id = pid, rid, svr or "76402e5b20be2c39f095a152090afddc"
                break

        if player_id and record_id:
            return f"player_id={player_id}&record_id={record_id}&svr_id={server_id}"
        return content[:8000]

    # ===================== 抽卡数据处理 =====================

    RESIDENT_FIVE_STAR = ["鉴心", "卡卡罗", "安可", "维里奈", "凌阳"]

    async def _format_gacha_pool(self, records: list) -> dict:
        """对标原项目 Gacha.js dataFormat，异步获取角色头像URL"""
        array = records
        if not array:
            return {"info": {"total": 0, "time": [None, None], "no5Star": 0, "no4Star": 0, "fiveStar": 0, "fourStar": 0, "std5Star": 0, "fourStarWpn": 0, "max4Star": "无", "avg5Star": 0, "avg4Star": 0, "avgUP": 0, "minPit": 0.0, "upCost": "0.00", "worstLuck": 0, "bestLuck": 0}, "pool": []}
        first5 = next((i for i, x in enumerate(array) if x.get("qualityLevel") == 5), -1)
        first4 = next((i for i, x in enumerate(array) if x.get("qualityLevel") == 4), -1)
        no5 = first5 if first5 >= 0 else len(array)
        no4 = first4 if first4 >= 0 else len(array)
        fl = [x for x in array if x.get("qualityLevel") == 5]
        f4 = [x for x in array if x.get("qualityLevel") == 4]
        f5n, f4n = len(fl), len(f4)
        std5 = sum(1 for x in fl if x.get("name") in self.RESIDENT_FIVE_STAR)
        f4w = sum(1 for x in f4 if x.get("resourceType") == "武器")
        cnt4 = {}
        for x in f4: n = x.get("name", "?"); cnt4[n] = cnt4.get(n, 0) + 1
        max4 = max(cnt4, key=cnt4.get) if cnt4 else "无"
        avg5 = round((len(array) - no5) / f5n) if f5n else 0
        avg4 = round((len(array) - no4) / f4n) if f4n else 0
        upc = f5n - std5
        avgU = round((len(array) - no5) / upc) if upc else 0
        first_std = 1 if fl and fl[0].get("name") in self.RESIDENT_FIVE_STAR else 0
        t5p = first_std + f5n
        minP = 0.0 if t5p == std5 else round((t5p - std5 * 2) / (t5p - std5) * 100, 1)
        upCost_ = f"{(avgU * 160 / 10000):.2f}"
        idx5 = [i for i, x in enumerate(array) if x.get("qualityLevel") == 5]
        gaps = [idx5[i] - idx5[i - 1] for i in range(1, len(idx5))]
        if idx5:
            gaps.append(len(array) - idx5[-1] - 1)
        bestL = min(gaps) if gaps else 0
        worstL = max(gaps) if gaps else 0

        # 批量获取五星角色头像
        avatar_cache = {}
        async def _get_avatar(name: str) -> str:
            if name in avatar_cache:
                return avatar_cache[name]
            try:
                r = await self.wiki.get_record(name)
                if r["status"]:
                    url = r["record"].get("content", {}).get("contentUrl", "")
                    avatar_cache[name] = url
                    return url
            except Exception:
                pass
            avatar_cache[name] = ""
            return ""

        # 去重后并行获取
        unique_names = list({x.get("name", "") for x in fl if x.get("name")})
        if unique_names:
            await asyncio.gather(*[_get_avatar(n) for n in unique_names])

        pool_list = [{"name": x.get("name", "?"), "times": next((j for j in range(array.index(x) + 1, len(array)) if array[j].get("qualityLevel") == 5), len(array)) - array.index(x), "isUp": x.get("name") not in self.RESIDENT_FIVE_STAR, "avatar": avatar_cache.get(x.get("name", ""), "")} for x in fl]
        return {"info": {"total": len(array), "time": [array[0].get("time"), array[-1].get("time")], "no5Star": no5, "no4Star": no4, "fiveStar": f5n, "fourStar": f4n, "std5Star": std5, "fourStarWpn": f4w, "max4Star": max4, "avg5Star": avg5, "avg4Star": avg4, "avgUP": avgU, "minPit": minP, "upCost": upCost_, "worstLuck": worstL, "bestLuck": bestL}, "pool": pool_list}

    async def _do_import_gacha(self, event: AstrMessageEvent, data: str) -> str:
        """解析各种格式的抽卡数据，查询API并缓存。返回结果字符串。"""
        json_data = {}
        data = data.strip()

        # Client.log
        if "OpenWebView" in data and "player_id" in data:
            pid = rid = svr = None
            for line in data.split("\n"):
                if "OpenWebView" not in line or "player_id" not in line:
                    continue
                m = re.search(r'https?://[^\s"]+', line)
                if not m:
                    continue
                url = m.group(0).rstrip('"')
                p = urlparse(url)
                qs = (p.fragment or p.query)
                params = parse_qs(qs.split("?", 1)[1]) if "?" in qs else {}
                pid = params.get("player_id", [None])[0]
                rid = params.get("record_id", [None])[0]
                svr = params.get("svr_id", [None])[0]
                if pid and rid:
                    pid, rid, svr = pid, rid, svr or "76402e5b20be2c39f095a152090afddc"
                    break
            if pid and rid:
                json_data = {"playerId": pid, "recordId": rid, "serverId": svr, "languageCode": "zh-Hans"}
            else:
                return "Client.log 中未找到抽卡记录链接。请确认已打开过游戏抽卡页面。"

        elif not json_data:
            # 查询字符串
            if re.match(r'^player[_]?[Ii]d=\d+&', data):
                params = parse_qs(data)
                pid = params.get("player_id", [None])[0] or params.get("playerId", [None])[0]
                rid = params.get("record_id", [None])[0] or params.get("recordId", [None])[0]
                svr = params.get("svr_id", [None])[0] or params.get("serverId", [None])[0]
                if pid and rid:
                    json_data = {"playerId": pid, "recordId": rid, "serverId": svr or "76402e5b20be2c39f095a152090afddc", "languageCode": "zh-Hans"}
                else:
                    return "无法从参数解析 player_id 或 record_id。"

            # URL
            elif re.search(r'https?://', data):
                url = re.search(r'https?://[^\s]+', data).group(0)
                p = urlparse(url)
                qs = (p.fragment or p.query)
                params = parse_qs(qs.split("?", 1)[1]) if "?" in qs else {}
                pid = params.get("player_id", [None])[0] or params.get("playerId", [None])[0]
                rid = params.get("record_id", [None])[0] or params.get("recordId", [None])[0]
                svr = params.get("svr_id", [None])[0] or params.get("serverId", [None])[0]
                if pid and rid:
                    json_data = {"playerId": pid, "recordId": rid, "serverId": svr or "76402e5b20be2c39f095a152090afddc", "languageCode": "zh-Hans"}
                else:
                    return "无法从链接解析 player_id 或 record_id。"

            # JSON
            else:
                try:
                    d = json.loads(data)
                    if d.get("playerId") and d.get("recordId"):
                        json_data = {"playerId": d["playerId"], "recordId": d["recordId"], "serverId": d.get("serverId", "76402e5b20be2c39f095a152090afddc"), "languageCode": d.get("languageCode", "zh-Hans")}
                    else:
                        return "JSON缺少 playerId 或 recordId 字段。"
                except json.JSONDecodeError:
                    return "无法识别格式。请提供 Client.log内容 / URL链接 / JSON请求体 / 查询参数。"

        if not json_data.get("playerId"):
            return "未能获取有效抽卡参数。"

        player_id = json_data["playerId"]
        record_id = json_data["recordId"]
        server_id = json_data["serverId"]
        language_code = json_data["languageCode"]
        logger.info(f"[Waves] 查询抽卡: UID={player_id}")

        pool_labels = {1: "角色", 2: "武器", 3: "常驻角色", 4: "常驻武器", 5: "新手", 6: "自选", 7: "感恩"}
        all_results = []
        failed = []
        for pool_id in range(1, 8):
            q = {"playerId": player_id, "serverId": server_id, "languageCode": language_code, "recordId": record_id, "cardPoolId": str(pool_id), "cardPoolType": str(pool_id)}
            d = await self.kuro.get_gacha(q)
            if d["status"] and isinstance(d["data"], list):
                for r in d["data"]:
                    r["gacha_id"] = pool_id
                all_results.extend(d["data"])
            else:
                failed.append(pool_labels.get(pool_id, str(pool_id)))

        if not all_results and failed:
            return f"所有卡池查询均失败: {', '.join(failed)}。recordId 可能已过期，请重新打开游戏抽卡页面后获取最新 Client.log。"

        # 保存缓存
        self.config_mgr.set_gacha_records(player_id, {
            "info": {"lang": "zh-cn", "region_time_zone": 8, "export_timestamp": int(datetime.now().timestamp() * 1000), "export_app": "Waves-AstrBot-Plugin", "export_app_version": "1.0.0", "wwgf_version": "v0.1b", "uid": player_id},
            "list": all_results,
        })

        # 构建展示数据
        pm = {1: "upCharPool", 2: "upWpnPool", 3: "stdCharPool", 4: "stdWpnPool", 5: "otherPool", 6: "upCharPool", 7: "otherPool"}
        gd = {"playerId": str(player_id)}
        total = 0
        for gid_key, recs in {g: [r for r in all_results if r["gacha_id"] == g] for g in {r["gacha_id"] for r in all_results}}.items():
            pkey = pm.get(gid_key, "otherPool")
            gd.setdefault(pkey, []).extend(recs)
        for k in list(gd.keys()):
            if k == "playerId": continue
            fmt = await self._format_gacha_pool(gd[k])
            total += fmt["info"]["total"]
            gd[k] = fmt

        result = f"导入成功！UID {player_id} 共 {total} 抽，已保存 {len(all_results)} 条记录。"
        lines = []
        for pk in ["upCharPool", "upWpnPool", "stdCharPool", "stdWpnPool", "otherPool"]:
            pd = gd.get(pk)
            if pd and isinstance(pd, dict) and pd.get("info", {}).get("total", 0) > 0:
                pl = {"upCharPool": "角色活动", "upWpnPool": "武器活动", "stdCharPool": "常驻角色", "stdWpnPool": "常驻武器", "otherPool": "其他"}.get(pk, pk)
                lines.append(f"{pl}: {pd['info']['total']}抽")
        if lines:
            result += "\n" + "\n".join(lines)
        return result

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
