"""声骸权重计算器 - 对标原项目 utils/Calculate.js"""
import yaml
from pathlib import Path


class WeightCalculator:
    """计算角色声骸评分和评级"""

    def __init__(self, role_detail: dict, resources_dir: Path, logger=None):
        self.role_detail = role_detail
        self.role_weight_path = resources_dir / "Weight" / f"{role_detail['role']['roleId']}.yaml"
        self.base_weight_path = resources_dir / "Weight" / "weight.yaml"
        self.logger = logger

    def calculate(self) -> dict:
        phantom_list = self.role_detail.get("phantomData", {}).get("equipPhantomList")
        if not isinstance(phantom_list, list):
            self.role_detail.setdefault("phantomData", {})["equipPhantomList"] = []
            phantom_list = []

        for phantom in phantom_list:
            if phantom is None:
                continue
            for tag_list_key in ("mainProps", "subProps"):
                for tag in phantom.get(tag_list_key) or []:
                    if tag["attributeName"] in ("攻击", "生命", "防御") and "%" in tag.get("attributeValue", ""):
                        tag["attributeName"] += "百分比"

        weapon_colors = {5: "#9d2933", 4: "#9f00ed", 3: "#6640ff", 2: "#00D200"}
        rl = self.role_detail.get("weaponData", {}).get("resonLevel", 0)
        self.role_detail.setdefault("weaponData", {})["color"] = weapon_colors.get(rl, "#a0a0a0")

        if not self.role_weight_path.exists():
            return self.role_detail

        with open(self.role_weight_path, "r", encoding="utf-8") as f:
            role_weight = yaml.safe_load(f)
        with open(self.base_weight_path, "r", encoding="utf-8") as f:
            base_weight = yaml.safe_load(f)
        self.role_detail["weightVersion"] = base_weight.get("version", "")

        self._cal_val_weight(role_weight, base_weight)
        self._cal_theoretical_value(role_weight)

        for phantom in phantom_list:
            if phantom:
                self._cal_phantom(phantom, role_weight, base_weight)

        self.role_detail["phantomData"]["statistic"] = self._gather_tags(phantom_list, role_weight)
        return self.role_detail

    def _cal_val_weight(self, rw, bw):
        def add_sub(name, base_max, base_pct_max, role_base, role_w_prop):
            rw.setdefault("subProps", []).append({
                "name": name,
                "weight": base_max / role_base / (base_pct_max / 100) * role_w_prop
            })
        def add_main(cost, name, base_max, base_pct_max, role_base, role_w_prop):
            rw.setdefault("mainProps", {}).setdefault(cost, []).append({
                "name": name,
                "weight": base_max / role_base / (base_pct_max / 100) * role_w_prop
            })
        bw_sub = {t["name"]: t for t in bw["subProps"]}
        rw_sub = {t["name"]: t for t in rw.get("subProps", [])}
        add_sub("攻击", bw_sub["攻击"]["max"], bw_sub["攻击百分比"]["max"],
                rw["baseAttack"], rw_sub["攻击百分比"]["weight"])
        add_sub("生命", bw_sub["生命"]["max"], bw_sub["生命百分比"]["max"],
                rw["baseHP"], rw_sub["生命百分比"]["weight"])
        add_sub("防御", bw_sub["防御"]["max"], bw_sub["防御百分比"]["max"],
                rw["baseDefense"], rw_sub["防御百分比"]["weight"])
        rw_main = rw.get("mainProps", {})
        bw_main = bw["mainProps"]
        for cost in ("C4", "C3"):
            add_main(cost, "攻击", bw_main[cost][0]["max"], bw_main[cost][1]["max"],
                     rw["baseAttack"], rw_main[cost][1]["weight"])
        add_main("C1", "生命", bw_main["C1"][0]["max"], bw_main["C1"][1]["max"],
                 rw["baseHP"], rw_main["C1"][1]["weight"])

    def _cal_theoretical_value(self, rw):
        factors = {"C4": 44, "C3": 30, "C1": 18}
        for tag in rw.get("subProps", []):
            tag["theoreticalValue"] = 21 * tag["weight"]
        for cost, factor in factors.items():
            for tag in rw.get("mainProps", {}).get(cost, []):
                tag["theoreticalValue"] = factor * tag["weight"]

    def _cal_phantom(self, phantom, rw, bw):
        total = 0
        rw_sub = {t["name"]: t for t in rw.get("subProps", [])}
        bw_sub = {t["name"]: t for t in bw["subProps"]}
        for tag in phantom.get("subProps") or []:
            sp = rw_sub.get(tag["attributeName"])
            if sp:
                val = float(tag["attributeValue"].replace("%", ""))
                total += val / bw_sub[tag["attributeName"]]["max"] * sp.get("theoreticalValue", 0)
                tag["color"] = self._cal_style(sp["weight"])
        rw_main = rw.get("mainProps", {})
        bw_main = bw["mainProps"]
        for tag in phantom.get("mainProps") or []:
            cost_key = f"C{phantom['cost']}"
            name = "伤害加成" if "伤害加成" in tag["attributeName"] else tag["attributeName"]
            try:
                val = float(tag["attributeValue"].replace("%", ""))
                total += val / bw_main[cost_key][0]["max"] * rw_main[cost_key][0].get("theoreticalValue", 0)
            except (KeyError, IndexError):
                if self.logger:
                    self.logger.warning(f"[Waves] 疑似该声骸属性异常: {phantom}")
        factor_map = {
            4: lambda: 22 + rw_main["C4"][0]["weight"] * rw_main["C3"][1].get("theoreticalValue", 0),
            3: lambda: 22.5 + rw_main["C3"][0].get("theoreticalValue", 0),
            1: lambda: 18 + rw_main["C1"][0].get("theoreticalValue", 0),
        }
        sorted_sub = sorted(rw.get("subProps", []), key=lambda t: t.get("theoreticalValue", 0), reverse=True)[:5]
        sub_factor = sum(t.get("theoreticalValue", 0) for t in sorted_sub)
        main_factor = factor_map.get(phantom["cost"], lambda: 0)()
        factor = 25 / (sub_factor + main_factor) if (sub_factor + main_factor) > 0 else 0
        phantom["realScore"] = factor * total
        phantom["rank"], phantom["color"] = self._cal_rank(phantom["realScore"])

    def _gather_tags(self, phantom_list, rw):
        defaults = ["暴击伤害", "暴击", "攻击百分比", "生命百分比", "防御百分比",
                     "共鸣效率", "普攻伤害加成", "重击伤害加成", "共鸣技能伤害加成",
                     "共鸣解放伤害加成", "攻击", "生命", "防御"]
        rw_sub = {t["name"]: t for t in rw.get("subProps", [])}
        dist = [{"name": n, "value": 0, "color": self._cal_style(rw_sub.get(n, {}).get("weight", 0))}
                for n in defaults]
        total = 0
        for p in phantom_list:
            if not p:
                continue
            total += p.get("realScore", 0)
            for tag in p.get("subProps") or []:
                idx = next((i for i, d in enumerate(dist) if d["name"] == tag["attributeName"]), -1)
                if idx >= 0:
                    dist[idx]["value"] += float(tag["attributeValue"].replace("%", ""))
        rank, color = self._cal_rank(total / 5 if phantom_list else 0)
        return {"totalScore": total, "dist": dist, "rank": rank, "color": color}

    @staticmethod
    def _cal_style(weight: float) -> str:
        if weight > 0.5:
            return "#9d2933"
        elif weight > 0:
            return "#057748"
        return "#a0a0a0"

    @staticmethod
    def _cal_rank(score: float):
        ranks = [
            (22, "MAX", "#9d2933"), (19, "ACE", "#f08a5d"),
            (17, "SSS", "#eec900"), (15, "SS", "#eec900"),
            (12, "S", "#eec900"), (9, "A", "#9f00ed"),
            (6, "B", "#6640ff"), (3, "C", "#00D200"),
            (0, "D", "#a0a0a0"),
        ]
        for min_score, name, color in ranks:
            if score >= min_score:
                return name, color
        return "D", "#a0a0a0"
