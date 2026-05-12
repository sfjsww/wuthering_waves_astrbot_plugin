"""配置管理模块 - 对标原项目 components/Config.js"""
import json
import yaml
from pathlib import Path


class ConfigManager:
    """管理插件配置、用户 Token 绑定、用户数据"""

    def __init__(self, astrbot_config: dict, data_dir: Path):
        self.data_dir = data_dir
        self._config_file = self.data_dir / "config.json"
        # 1. 加载 schema 默认值
        self._astrbot_config = self._load_schema_defaults()
        # 2. 合并 AstrBot 传入的配置（WebUI 修改的值）
        if astrbot_config:
            self._astrbot_config.update(astrbot_config)
        # 3. 用本地持久化配置覆盖（最高优先级）
        if self._config_file.exists():
            with open(self._config_file, "r", encoding="utf-8") as f:
                self._astrbot_config.update(json.load(f))
        self.users_dir = self.data_dir / "users"
        self.gacha_dir = self.data_dir / "gacha"
        self.signin_dir = self.data_dir / "signin"
        self._ensure_dirs()

    def _load_schema_defaults(self) -> dict:
        """从 _conf_schema.json 加载默认配置值"""
        schema_path = Path(__file__).parent.parent / "_conf_schema.json"
        defaults = {}
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            for key, prop in schema.items():
                if isinstance(prop, dict) and "default" in prop:
                    defaults[key] = prop["default"]
        return defaults

    def _ensure_dirs(self):
        for d in [self.data_dir, self.users_dir, self.gacha_dir, self.signin_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def get_config(self) -> dict:
        return dict(self._astrbot_config)

    def set_config(self, key: str, value):
        self._astrbot_config[key] = value
        # 持久化到文件
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(self._astrbot_config, f, ensure_ascii=False, indent=2)

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
