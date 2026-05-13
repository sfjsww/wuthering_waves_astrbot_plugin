/**
 * 鸣潮插件渲染 Worker — 完全复现原 waves-plugin components/Render.js 渲染管线
 * 通过 stdin/stdout JSON 协议接收渲染请求
 */
const artTemplate = require('art-template');
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

artTemplate.defaults.escape = false;

const OUTPUT_DIR = '/tmp/waves_render';
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

let browser = null;
let pendingCount = 0;
let stdinClosed = false;

async function ensureBrowser() {
    if (!browser) {
        browser = await puppeteer.launch({
            headless: true,
            executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium',
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--allow-file-access-from-files'],
        });
    }
    return browser;
}

async function render(req) {
    const { template: templateName, params, resources_dir, saveId, scale } = req;

    const tplDir = path.join(resources_dir, 'Template', templateName);
    const tplFile = path.join(tplDir, `${templateName}.html`);
    if (!fs.existsSync(tplFile)) throw new Error(`模板不存在: ${tplFile}`);

    let html = fs.readFileSync(tplFile, 'utf-8');
    const layoutPath = path.join(resources_dir, 'common', 'layout');

    // 复现原 Render.js beforeRender 逻辑
    const renderData = {
        ...params,
        pluginResources: `file://${resources_dir}`,
        _res_path: `file://${tplDir}/`,
        _layout_path: `file://${layoutPath}/`,
        defaultLayout: `file://${layoutPath}/default.html`,
        elemLayout: `file://${layoutPath}/elem.html`,
        sys: { scale: `style=transform:scale(${scale || 1});` },
        saveId: saveId || `${templateName}_1`,
        copyright: 'Created By waves-plugin',
    };

    try {
        html = artTemplate.render(html, renderData);
    } catch (e) {
        throw new Error(`模板语法错误: ${e.message}`);
    }

    const tmpDir = path.join(resources_dir, '.render_tmp');
    fs.mkdirSync(tmpDir, { recursive: true });
    const tmpFile = path.join(tmpDir, `${templateName}_${Date.now()}.html`);
    fs.writeFileSync(tmpFile, html, 'utf-8');

    const b = await ensureBrowser();
    const page = await b.newPage();
    try {
        await page.goto(`file://${tmpFile}`, { waitUntil: 'load', timeout: 15000 });
        await new Promise(r => setTimeout(r, 2000));
        const outputPath = path.join(OUTPUT_DIR, `${templateName}_${Date.now()}.png`);
        await page.screenshot({ path: outputPath, fullPage: true });
        return { path: outputPath };
    } finally {
        await page.close();
        try { fs.unlinkSync(tmpFile); } catch (_) { /* ignore */ }
    }
}

function writeResult(data) { process.stdout.write(JSON.stringify(data) + '\n'); }
function tryExit() {
    if (stdinClosed && pendingCount === 0) {
        if (browser) { browser.close().then(() => { browser = null; process.exit(0); }); }
        else { process.exit(0); }
    }
}

let buffer = '';
process.stdin.setEncoding('utf-8');
process.stdin.on('data', async chunk => {
    buffer += chunk;
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        let req;
        try { req = JSON.parse(trimmed); }
        catch (e) { writeResult({ status: 'error', error: `JSON解析失败: ${e.message}` }); continue; }
        pendingCount++;
        try {
            const result = await render(req);
            writeResult({ status: 'ok', path: result.path });
        } catch (err) {
            writeResult({ status: 'error', error: err.message });
        } finally {
            pendingCount--;
            tryExit();
        }
    }
});
process.stdin.on('end', () => { stdinClosed = true; tryExit(); });
process.stdin.on('error', () => { stdinClosed = true; tryExit(); });
