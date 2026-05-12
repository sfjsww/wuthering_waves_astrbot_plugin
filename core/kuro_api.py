"""库街区 API 客户端 - 对标原项目 components/Code.js"""
import json
import random
import string
import uuid
from datetime import datetime
import aiohttp


class KuroApi:
    """封装所有库街区 HTTP API 调用"""

    LOGIN_URL = "/user/sdkLogin"
    REFRESH_URL = "/aki/roleBox/akiBox/refreshData"
    TOKEN_REFRESH_URL = "/aki/roleBox/requestToken"
    GAME_DATA_URL = "/gamer/widget/game3/refresh"
    BASE_DATA_URL = "/aki/roleBox/akiBox/baseData"
    ROLE_DATA_URL = "/aki/roleBox/akiBox/roleData"
    CALABASH_DATA_URL = "/aki/roleBox/akiBox/calabashData"
    CHALLENGE_DATA_URL = "/aki/roleBox/akiBox/challengeDetails"
    EXPLORE_DATA_URL = "/aki/roleBox/akiBox/exploreIndex"
    SIGNIN_URL = "/encourage/signIn/v2"
    QUERY_RECORD_URL = "/encourage/signIn/queryRecordV2"
    GACHA_URL = "https://gmserver-api.aki-game2.com/gacha/record/query"
    INTL_GACHA_URL = "https://gmserver-api.aki-game2.net/gacha/record/query"
    ROLE_DETAIL_URL = "/aki/roleBox/akiBox/getRoleDetail"
    EVENT_LIST_URL = "/forum/companyEvent/findEventList"
    SELF_TOWER_DATA_URL = "/aki/roleBox/akiBox/towerDataDetail"
    OTHER_TOWER_DATA_URL = "/aki/roleBox/akiBox/towerIndex"

    def __init__(self, config_mgr, logger):
        self.config_mgr = config_mgr
        self.logger = logger
        self.bat = None
        self._session = None
        self._distinct_id = str(uuid.uuid4())
        self._dev_code = ''.join(random.choices('0123456789ABCDEF', k=40))

    @property
    def _reverse_url(self) -> str:
        return self.config_mgr.get_config().get("reverse_proxy_url", "https://api.kurobbs.com")

    @property
    def _proxy(self) -> str | None:
        return self.config_mgr.get_config().get("proxy_url") or None

    @property
    def _enable_log(self) -> bool:
        return self.config_mgr.get_config().get("enable_log", False)

    @property
    def _base_headers(self) -> dict:
        return {
            "source": "android",
            "version": "2.2.0",
            "versionCode": "2200",
            "osVersion": "Android",
            "distinct_id": self._distinct_id,
            "countryCode": "CN",
            "model": "23127PN0CC",
            "lang": "zh-Hans",
            "channelId": "2",
            "devCode": self._dev_code,
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _post(self, url: str, data: dict, headers: dict | None = None) -> dict:
        """统一 POST 请求，复用 session 保持 cookie"""
        full_url = url if url.startswith("http") else self._reverse_url + url
        all_headers = {**self._base_headers, **(headers or {})}
        session = await self._get_session()
        async with session.post(full_url, data=data, headers=all_headers,
                                 proxy=self._proxy) as resp:
            return await resp.json()

    async def get_token(self, mobile: str, code: str) -> dict:
        dev_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=40))
        data = {"mobile": mobile, "code": code}
        try:
            resp = await self._post(self.LOGIN_URL, data, {"devCode": dev_code})
            if resp.get("code") == 200:
                if self._enable_log:
                    self.logger.info(f"[Waves] 验证码登录成功: {resp['data']['userName']}")
                return {"status": True, "data": resp["data"]}
            self.logger.error(f"[Waves] 验证码登录失败: {resp.get('msg')}")
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            self.logger.error(f"[Waves] 验证码登录网络错误: {e}")
            return {"status": False, "msg": "登录失败，疑似网络问题"}

    async def is_available(self, server_id: str, role_id: str, token: str) -> bool:
        """对标 Code.js isAvailable: 仅 code=220 为过期，其余均视为可用"""
        data = {"serverId": server_id, "roleId": role_id}
        try:
            resp = await self._post(self.TOKEN_REFRESH_URL, data, {"token": token})
            if resp.get("code") == 220:
                return False
            if resp.get("data"):
                try:
                    self.bat = json.loads(resp["data"]).get("accessToken")
                except Exception:
                    pass
            return True
        except Exception:
            return True

    async def refresh_data(self, server_id: str, role_id: str, token: str) -> dict:
        """刷新游戏数据。非关键操作，失败不影响后续 API 调用"""
        data = {"gameId": 3, "serverId": server_id, "roleId": role_id}
        headers = {"token": token}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(self.REFRESH_URL, data, headers)
            if resp.get("code") in (200, 10902):
                return {"status": True, "data": resp.get("data")}
            # code 10000/10900 等不影响后续 API，降级为 debug
            return {"status": True, "data": None}
        except Exception:
            return {"status": True, "data": None}

    async def get_game_data(self, token: str) -> dict:
        data = {"type": "2", "sizeType": "1"}
        headers = {"token": token}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(self.GAME_DATA_URL, data, headers)
            if resp.get("code") == 200:
                if resp.get("data") is None:
                    return {"status": False, "msg": "查询失败，请检查对外展示开关"}
                return {"status": True, "data": resp["data"]}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            self.logger.error(f"[Waves] 获取日常数据网络错误: {e}")
            return {"status": False, "msg": "获取日常数据失败，疑似网络问题"}

    async def get_base_data(self, server_id: str, role_id: str, token: str) -> dict:
        await self.refresh_data(server_id, role_id, token)
        data = {"gameId": 3, "serverId": server_id, "roleId": role_id}
        headers = {"token": token}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(self.BASE_DATA_URL, data, headers)
            if resp.get("code") in (200, 10902):
                parsed = json.loads(resp["data"])
                if parsed is None or not parsed.get("showToGuest"):
                    return {"status": False, "msg": "查询失败，请检查对外展示开关"}
                return {"status": True, "data": parsed}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            self.logger.error(f"[Waves] 获取我的资料网络错误: {e}")
            return {"status": False, "msg": "获取我的资料失败，疑似网络问题"}

    async def get_role_data(self, server_id: str, role_id: str, token: str) -> dict:
        await self.refresh_data(server_id, role_id, token)
        data = {"gameId": 3, "serverId": server_id, "roleId": role_id}
        headers = {"token": token}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(self.ROLE_DATA_URL, data, headers)
            if resp.get("code") in (200, 10902):
                parsed = json.loads(resp["data"])
                if parsed is None or not parsed.get("showToGuest"):
                    return {"status": False, "msg": "查询失败，请检查对外展示开关"}
                return {"status": True, "data": parsed}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            self.logger.error(f"[Waves] 获取共鸣者列表网络错误: {e}")
            return {"status": False, "msg": "获取共鸣者列表失败，疑似网络问题"}

    async def get_role_detail(self, server_id: str, role_id: str, role_detail_id: str, token: str) -> dict:
        await self.refresh_data(server_id, role_id, token)
        data = {"serverId": server_id, "roleId": role_id, "id": role_detail_id}
        headers = {"token": token}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(self.ROLE_DETAIL_URL, data, headers)
            if resp.get("code") in (200, 10902):
                parsed = json.loads(resp["data"])
                if parsed is None:
                    return {"status": False, "msg": "查询失败，请检查对外展示开关"}
                return {"status": True, "data": parsed}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            self.logger.error(f"[Waves] 获取角色详情网络错误: {e}")
            return {"status": False, "msg": "获取角色详情失败，疑似网络问题"}

    async def _query_section(self, url: str, server_id: str, role_id: str, token: str, extra_data: dict = None, check_open: bool = True) -> dict:
        await self.refresh_data(server_id, role_id, token)
        data = {"gameId": 3, "serverId": server_id, "roleId": role_id, **(extra_data or {})}
        headers = {"token": token}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(url, data, headers)
            if resp.get("code") in (200, 10902):
                parsed = json.loads(resp["data"])
                if parsed is None:
                    return {"status": False, "msg": "查询失败，请检查对外展示开关"}
                if check_open and not parsed.get("open", True):
                    return {"status": False, "msg": "查询失败，请检查对外展示开关"}
                return {"status": True, "data": parsed}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            self.logger.error(f"[Waves] 查询板块网络错误: {e}")
            return {"status": False, "msg": "查询失败，疑似网络问题"}

    async def get_calabash_data(self, server_id: str, role_id: str, token: str) -> dict:
        return await self._query_section(self.CALABASH_DATA_URL, server_id, role_id, token, check_open=False)

    async def get_challenge_data(self, server_id: str, role_id: str, token: str) -> dict:
        return await self._query_section(self.CHALLENGE_DATA_URL, server_id, role_id, token, {"countryCode": 1})

    async def get_explore_data(self, server_id: str, role_id: str, token: str) -> dict:
        return await self._query_section(self.EXPLORE_DATA_URL, server_id, role_id, token, {"countryCode": 1})

    async def get_tower_data(self, server_id: str, role_id: str, token: str) -> dict:
        result = await self._query_section(self.SELF_TOWER_DATA_URL, server_id, role_id, token, check_open=False)
        if result["status"]:
            return result
        try:
            data = {"gameId": 3, "serverId": server_id, "roleId": role_id}
            headers = {"token": token}
            if self.bat:
                headers["b-at"] = self.bat
            resp = await self._post(self.OTHER_TOWER_DATA_URL, data, headers)
            if resp.get("code") == 200:
                parsed = json.loads(resp["data"])
                if parsed is None:
                    return {"status": False, "msg": "查询失败，请检查对外展示开关"}
                return {"status": True, "data": parsed}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            return {"status": False, "msg": str(e)}

    async def sign_in(self, server_id: str, role_id: str, user_id: str, token: str) -> dict:
        await self.refresh_data(server_id, role_id, token)
        month = datetime.now().strftime("%m")
        data = {"gameId": 3, "serverId": server_id, "roleId": role_id, "userId": user_id, "reqMonth": month}
        headers = {"token": token, "devcode": ""}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(self.SIGNIN_URL, data, headers)
            if resp.get("code") == 200:
                if resp.get("data") is None:
                    return {"status": False, "msg": "签到失败，返回空数据"}
                return {"status": True, "data": resp["data"]}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            self.logger.error(f"[Waves] 签到网络错误: {e}")
            return {"status": False, "msg": "签到失败，疑似网络问题"}

    async def query_record(self, server_id: str, role_id: str, token: str) -> dict:
        await self.refresh_data(server_id, role_id, token)
        data = {"gameId": 3, "serverId": server_id, "roleId": role_id}
        headers = {"token": token}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(self.QUERY_RECORD_URL, data, headers)
            if resp.get("code") == 200:
                if resp.get("data") is None:
                    return {"status": False, "msg": "查询失败，返回空数据"}
                return {"status": True, "data": resp["data"]}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            return {"status": False, "msg": str(e)}

    async def get_gacha(self, query_data: dict) -> dict:
        is_cn = query_data.get("serverId") == "76402e5b20be2c39f095a152090afddc"
        url = self.GACHA_URL if is_cn else self.INTL_GACHA_URL
        try:
            resp = await self._post(url, query_data)
            if resp.get("code") == 0:
                if resp.get("data") is None:
                    return {"status": False, "msg": "查询失败，返回空数据"}
                return {"status": True, "data": resp["data"]}
            return {"status": False, "msg": resp.get("message")}
        except Exception as e:
            return {"status": False, "msg": str(e)}

    async def get_event_list(self, event_type: int = 0) -> dict:
        data = {"gameId": 3, "eventType": event_type}
        headers = {}
        if self.bat:
            headers["b-at"] = self.bat
        try:
            resp = await self._post(self.EVENT_LIST_URL, data, headers)
            if resp.get("code") == 200:
                if resp.get("data") is None:
                    return {"status": False, "msg": "查询失败，返回空数据"}
                return {"status": True, "data": resp["data"]}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            return {"status": False, "msg": str(e)}

    async def close(self):
        """关闭 HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

