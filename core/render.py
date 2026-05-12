"""HTML -> 图片渲染模块 - 对标原项目 components/Render.js"""
import time
from pathlib import Path

_browser = None
_time_counter: dict[str, int] = {}


def _get_save_id(name: str) -> str:
    if name not in _time_counter:
        _time_counter[name] = 0
    _time_counter[name] += 1
    return f"{name}_{_time_counter[name]}"


class Render:
    """Playwright HTML 渲染器"""

    def __init__(self, resources_dir: Path, config_mgr):
        self.resources_dir = resources_dir
        self.config_mgr = config_mgr

    async def render(self, template_name: str, params: dict) -> str:
        """渲染 HTML 模板并返回图片路径"""
        template_path = self.resources_dir / "Template" / template_name
        layout_path = self.resources_dir / "common" / "layout"
        scale = min(2, max(0.5, self.config_mgr.get_config().get("render_scale", 100) / 100))

        # 模板文件命名规则: Template/<name>/<name>.html
        html_file = template_path / f"{template_name}.html"
        if not html_file.exists():
            raise FileNotFoundError(f"模板不存在: {html_file}")
        html_content = html_file.read_text(encoding="utf-8")

        html_content = html_content.replace("{{pluginResources}}", str(self.resources_dir))
        html_content = html_content.replace("{{_res_path}}", str(template_path))
        html_content = html_content.replace("{{_layout_path}}", str(layout_path) + "/")
        html_content = html_content.replace("{{defaultLayout}}", f"{layout_path}/default.html")
        html_content = html_content.replace("{{elemLayout}}", f"{layout_path}/elem.html")

        save_id = _get_save_id(params.get("saveId", template_name))
        html_content = html_content.replace("{{saveId}}", save_id)

        import json
        for key, value in params.items():
            if isinstance(value, (dict, list)):
                html_content = html_content.replace(f"{{{{{key}}}}}", json.dumps(value, ensure_ascii=False))
            else:
                html_content = html_content.replace(f"{{{{{key}}}}}", str(value))

        from playwright.async_api import async_playwright
        global _browser
        if _browser is None:
            p = await async_playwright().start()
            _browser = await p.chromium.launch(headless=True)

        page = await _browser.new_page(viewport={"width": 800, "height": 600})
        await page.set_content(html_content, wait_until="networkidle")
        await page.evaluate(f"document.body.style.transform = 'scale({scale})'")

        output_dir = Path("/tmp/waves_render")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{template_name.replace('/', '_')}_{int(time.time())}.png"
        await page.screenshot(path=str(output_file), full_page=True)
        await page.close()

        return str(output_file)
