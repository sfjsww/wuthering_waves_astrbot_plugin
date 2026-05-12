"""waves_simulate_gacha - 对标 apps/Simulator.js"""
from astrbot.api.event import filter, AstrMessageEvent
import yaml, random

def register_simulate_gacha_tool(plugin):
    @filter.llm_tool(name="waves_simulate_gacha")
    async def waves_simulate_gacha(self, event: AstrMessageEvent, pool_type: str = "角色", count: str = "十连"):
        '''模拟鸣潮抽卡，仅供娱乐。Args: pool_type(string, optional): "角色"或"武器", count(string, optional): "单抽"或"十连"'''
        sim_dir = plugin.render.resources_dir / "Simulator"
        pool_map = {"角色": "role.yaml", "武器": "weapon.yaml"}
        pool_file = pool_map.get(pool_type, "role.yaml")
        with open(sim_dir / pool_file, "r", encoding="utf-8") as f:
            pool_data = yaml.safe_load(f)
        times = 10 if count == "十连" else 1
        results = []
        for _ in range(times):
            roll = random.random()
            if roll < 0.008:
                candidates = [r for r in pool_data if r.get("star") == 5]
            elif roll < 0.08:
                candidates = [r for r in pool_data if r.get("star") == 4]
            else:
                candidates = [r for r in pool_data if r.get("star") == 3]
            result = random.choice(candidates) if candidates else {"name": "?", "star": 3}
            results.append(f"{'⭐'*result['star']} {result['name']}")
        yield event.plain_result(f"模拟{pool_type}池{count}结果：\n" + "\n".join(results))
    plugin.register_tool("waves_simulate_gacha", waves_simulate_gacha, "_tool_simulate_gacha")
