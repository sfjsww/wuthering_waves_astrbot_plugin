"""HTML → 图片渲染模块 — 通过 Node.js worker 复用原插件 art-template + Puppeteer 管线"""
import asyncio
import json
import time
from pathlib import Path


class Render:
    """渲染器，对标原项目 components/Render.js"""

    def __init__(self, resources_dir: Path, config_mgr):
        self.resources_dir = resources_dir
        self.config_mgr = config_mgr
        self._proc = None
        self._lock = asyncio.Lock()
        self._time_counter: dict[str, int] = {}
        self._worker_script = Path(__file__).parent.parent / "render_worker.js"

    def _get_save_id(self, name: str) -> str:
        if name not in self._time_counter:
            self._time_counter[name] = 0
        self._time_counter[name] += 1
        return f"{name}_{self._time_counter[name]}"

    async def _ensure_worker(self):
        if self._proc is not None and self._proc.returncode is not None:
            self._proc = None
        if self._proc is None:
            self._proc = await asyncio.create_subprocess_exec(
                "node", str(self._worker_script),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

    async def render(self, template_name: str, params: dict) -> str:
        """渲染 HTML 模板并返回图片路径。
        对标原项目 Render.render(path, params, cfg) 的 beforeRender 逻辑。
        """
        scale = min(2.0, max(0.5, self.config_mgr.get_config().get("render_scale", 100) / 100))

        request = {
            "template": template_name,
            "params": dict(params),
            "resources_dir": str(self.resources_dir),
            "saveId": self._get_save_id(params.get("saveId", template_name)),
            "scale": scale,
        }

        async with self._lock:
            last_err = None
            for attempt in range(3):
                try:
                    await self._ensure_worker()
                    self._proc.stdin.write((json.dumps(request, ensure_ascii=False) + "\n").encode())
                    await self._proc.stdin.drain()
                    resp_line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=45.0)
                    resp = json.loads(resp_line.decode())
                    if resp.get("status") == "ok":
                        return resp["path"]
                    last_err = resp.get("error", "未知渲染错误")
                except (BrokenPipeError, ConnectionResetError, OSError, asyncio.TimeoutError) as e:
                    self._proc = None
                    last_err = str(e)
                    if attempt < 2:
                        await asyncio.sleep(0.5)

        raise RuntimeError(f"渲染失败: {last_err}")

    async def close(self):
        if self._proc is not None:
            try: self._proc.stdin.close()
            except Exception: pass
            try: await asyncio.wait_for(self._proc.wait(), timeout=3.0)
            except asyncio.TimeoutError: self._proc.kill(); await self._proc.wait()
            self._proc = None
