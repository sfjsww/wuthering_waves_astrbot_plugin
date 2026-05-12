"""HTTP 登录服务器 - 对标原项目 components/Server.js"""
from aiohttp import web
from pathlib import Path


class LoginServer:
    """管理 HTTP 登录服务器生命周期"""

    def __init__(self, config_mgr, kuro_api, resources_dir: Path, logger):
        self.config_mgr = config_mgr
        self.kuro = kuro_api
        self.resources_dir = resources_dir
        self.logger = logger
        self.app = web.Application()
        self.runner = None
        self._pending_logins: dict[str, dict] = {}

    async def start(self):
        if not self.config_mgr.get_config().get("allow_login", False):
            return
        self.app.router.add_get("/login/{id}", self._serve_login_page)
        self.app.router.add_post("/code/{id}", self._handle_code)
        self.app.router.add_route("*", "/{tail:.*}", self._fallback)
        port = self.config_mgr.get_config().get("server_port", 25088)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", port)
        await site.start()
        self.logger.info(f"[Waves] 登录服务器已启动，端口: {port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            self.logger.info("[Waves] 登录服务器已关闭")

    async def _serve_login_page(self, request: web.Request):
        login_id = request.match_info["id"]
        user_data = self._pending_logins.get(login_id)
        file_path = self.resources_dir / "server" / ("login.html" if user_data else "error.html")
        try:
            content = file_path.read_text(encoding="utf-8")
            if user_data:
                content = content.replace("undefined", str(user_data.get("user_id", "")))
            bg = self.config_mgr.get_config().get("background_api", "")
            content = content.replace("background_image", bg)
            return web.Response(text=content, content_type="text/html")
        except Exception as e:
            return web.Response(text=f"Internal Server Error: {e}", status=500)

    async def _handle_code(self, request: web.Request):
        login_id = request.match_info["id"]
        if login_id not in self._pending_logins:
            return web.json_response({"code": 400, "msg": "Authorization required"})
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"code": 400, "msg": "Invalid body"})
        mobile = body.get("mobile", "")
        code = body.get("code", "")
        if not mobile or not code:
            return web.json_response({"code": 400, "msg": "无法获取手机号和验证码"})
        result = await self.kuro.get_token(mobile, code)
        if result["status"]:
            token = result["data"]["token"]
            user_id = str(result["data"].get("userId", ""))
            qq_id = self._pending_logins[login_id].get("qq_id", "")
            server_id = "76402e5b20be2c39f095a152090afddc"  # 默认国服
            # 通过 get_game_data 获取正确的游戏 roleId
            role_id = user_id
            try:
                gd = await self.kuro._post('/gamer/widget/game3/refresh',
                    {'type': '2', 'sizeType': '1'}, {'token': token})
                if gd.get('code') == 200 and gd.get('data'):
                    role_id = str(gd['data'].get('roleId', user_id))
                    role_name = gd['data'].get('roleName', '')
                    self.logger.info(f"[Waves] 发现角色: roleId={role_id} name={role_name}")
            except Exception as e:
                self.logger.error(f"[Waves] 获取角色失败: {e}")
            account = {
                "serverId": server_id,
                "roleId": role_id,
                "userId": user_id,
                "token": token,
            }
            tokens = self.config_mgr.get_user_tokens(qq_id)
            tokens = [t for t in tokens if t.get("roleId") != account["roleId"]]
            tokens.append(account)
            self.config_mgr.set_user_tokens(qq_id, tokens)
            self.logger.info(f"[Waves] 用户 {qq_id} 登录成功, 库街区ID={user_id}, Token已保存。请通过 bind_uid 绑定正确的游戏UID。")
            self._pending_logins[login_id]["token"] = token
            return web.json_response({"code": 200, "msg": f"登录成功！你的库街区ID: {user_id}。在QQ群发送「绑定UID 你的9位游戏UID」来绑定正确的游戏角色。"})
        return web.json_response({"code": 400, "msg": result.get("msg", "登录失败")})

    async def _fallback(self, request: web.Request):
        raise web.HTTPFound("https://github.com/sfjsww/wuthering_waves_astrbot_plugin")

    def create_login_session(self, login_id: str, user_id: str, qq_id: str):
        self._pending_logins[login_id] = {"user_id": user_id, "qq_id": qq_id}
        cfg = self.config_mgr.get_config()
        public_link = cfg.get("public_link", "http://127.0.0.1:25088")
        self.logger.info(f"[Waves] create_login_session: public_link={public_link}, all_keys_in_cfg={list(cfg.keys())[:5]}...")
        return f"{public_link}/login/{login_id}"

    def get_session_result(self, login_id: str) -> dict | None:
        session = self._pending_logins.get(login_id)
        if session and session.get("token"):
            result = dict(session)
            del self._pending_logins[login_id]
            return result
        return None
