"""配置管理模块 - 对标原项目 components/Config.js"""
import yaml
from pathlib import Path


class ConfigManager:
    """管理插件配置、用户 Token 绑定、用户数据"""

    def __init__(self, astrbot_config: dict, data_dir: Path):
        self._astrbot_config = astrbot_config
        self.data_dir = data_dir
        self.users_dir = self.data_dir / "users"
        self.gacha_dir = self.data_dir / "gacha"
        self.signin_dir = self.data_dir / "signin"
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in [self.data_dir, self.users_dir, self.gacha_dir, self.signin_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def get_config(self) -> dict:
        return dict(self._astrbot_config)

    def set_config(self, key: str, value):
        self._astrbot_config[key] = value
        self._astrbot_config.save_config()

    def get_user_tokens(self, user_id: str) -> list:
        file_path = self.users_dir / f"{user_id}.yaml"
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, list) else []

    def set_user_tokens(self, user_id: str, tokens: list):
        file_path = self.users_dir / f"{user_id}.yaml"
        if not tokens:
            if file_path.exists():
                file_path.unlink()
            return
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(tokens, f, allow_unicode=True, default_flow_style=False)

    def get_gacha_records(self, uid: str) -> dict | None:
        import json
        file_path = self.gacha_dir / f"{uid}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def set_gacha_records(self, uid: str, data: dict):
        import json
        file_path = self.gacha_dir / f"{uid}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_signin_records(self, uid: str) -> dict | None:
        import json
        file_path = self.signin_dir / f"{uid}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def set_signin_records(self, uid: str, data: dict):
        import json
        file_path = self.signin_dir / f"{uid}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def get_public_cookie(self, kuro_api):
        """获取一个可用的公共 Token（对标 Code.js pubCookie）"""
        if not self.get_config().get("use_public_cookie", True):
            return None
        all_tokens = []
        for f in self.users_dir.glob("*.yaml"):
            tokens = self.get_user_tokens(f.stem)
            all_tokens.extend(tokens)
        import random
        random.shuffle(all_tokens)
        for token_data in all_tokens:
            if token_data.get("token"):
                ok = await kuro_api.is_available(
                    token_data["serverId"],
                    token_data["roleId"],
                    token_data["token"]
                )
                if ok:
                    return token_data
        return None

    def get_all_bound_users(self) -> dict[str, list]:
        result = {}
        for f in self.users_dir.glob("*.yaml"):
            tokens = self.get_user_tokens(f.stem)
            if tokens:
                result[f.stem] = tokens
        return result
