"""Wiki 查询 + 别名解析 - 对标原项目 components/Wiki.js"""
import asyncio
import yaml
from pathlib import Path


class Wiki:
    """封装库街区 Wiki API 和别名解析"""

    CATALOGUEID_MAP = {
        "1105": "共鸣者", "1106": "武器", "1107": "声骸",
        "1219": "合鸣效果", "1158": "敌人", "1264": "可合成道具",
        "1265": "道具合成图纸", "1217": "补给", "1161": "资源",
        "1218": "素材", "1223": "特殊道具",
    }

    WIKI_PAGE_URL = "/wiki/core/catalogue/item/getPage"
    WIKI_ENTRYDETAIL_URL = "/wiki/core/catalogue/item/getEntryDetail"
    WIKI_SEARCH_URL = "/wiki/core/catalogue/item/search"

    def __init__(self, resources_dir: Path, kuro_api, logger):
        self.resources_dir = resources_dir
        self.kuro = kuro_api
        self.logger = logger

    def get_alias(self, name: str) -> str:
        """通过别名查找角色正式名称"""
        alias_dirs = [
            self.resources_dir / "Alias",
            self.resources_dir / "Alias" / "custom",
        ]
        for d in alias_dirs:
            if not d.exists():
                continue
            for f in d.glob("*.yaml"):
                with open(f, "r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not data:
                    continue
                for key, values in data.items():
                    if name in values:
                        return key
        return name

    async def get_page(self, catalogue_id: str) -> dict:
        data = {"catalogueId": catalogue_id, "limit": 1000}
        headers = {"wiki_type": "9"}
        try:
            resp = await self.kuro._post(self.WIKI_PAGE_URL, data, headers)
            if resp.get("code") == 200:
                return {"status": True, "data": resp["data"]}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            return {"status": False, "msg": str(e)}

    async def get_record(self, name: str, item_type: str = "") -> dict:
        if item_type:
            resp = await self.get_page(item_type)
            if resp["status"]:
                for record in resp["data"]["results"]["records"]:
                    if record["name"] == name:
                        return {"status": True, "record": record, "type": item_type}
            return {"status": False, "msg": "未找到该词条的Wiki信息"}
        tasks = [self.get_page(cid) for cid in self.CATALOGUEID_MAP]
        responses = await asyncio.gather(*tasks)
        for i, resp in enumerate(responses):
            cid = list(self.CATALOGUEID_MAP.keys())[i]
            if resp["status"]:
                for record in resp["data"]["results"]["records"]:
                    if record["name"] == name:
                        return {"status": True, "record": record, "type": cid}
        return {"status": False, "msg": "未找到该词条的Wiki信息"}

    async def get_entry(self, name: str, item_type: str = "") -> dict:
        record_data = await self.get_record(name, item_type)
        if not record_data["status"]:
            return record_data
        link_id = record_data["record"]["content"]["linkId"]
        data = {"id": link_id}
        try:
            resp = await self.kuro._post(self.WIKI_ENTRYDETAIL_URL, data, {"wiki_type": "9"})
            if resp.get("code") == 200:
                return {"status": True, "record": resp["data"], "type": record_data["type"]}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            return {"status": False, "msg": str(e)}

    async def search(self, keyword: str) -> dict:
        data = {"keyword": keyword, "limit": 1000}
        try:
            resp = await self.kuro._post(self.WIKI_SEARCH_URL, data, {"wiki_type": "9"})
            if resp.get("code") == 200:
                if resp["data"].get("results") is None:
                    return {"status": False, "msg": "未找到该词条的Wiki信息"}
                return {"status": True, "data": resp["data"]}
            return {"status": False, "msg": resp.get("msg")}
        except Exception as e:
            return {"status": False, "msg": str(e)}
