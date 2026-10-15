// 采集 VS Code 自带主题下全部颜色键的实际取值(工作台 CSS 变量 --vscode-*), 作为颜色键分层复核页的"系统默认"参考.
// 借 tools/shoot.mjs 常驻进程的截图实例(调试端口 SHOOT_PORT, 默认 9333): 改它的设置文件切主题, 读完不还原(下一个截图任务会重写设置).
// 常驻进程正在跑任务时不要运行.
// 用法: node tools/capture-vars.mjs <输出 json> [主题设置 ID...]   默认采 Default Dark Modern / Default Light Modern / Default Dark+ / Default Light+
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright-core';

const [outArg, ...ids] = process.argv.slice(2);
if (!outArg) {
  console.error('用法: node tools/capture-vars.mjs <输出 json> [主题设置 ID...]');
  process.exit(2);
}
const themes = ids.length ? ids : ['Default Dark Modern', 'Default Light Modern', 'Default Dark+', 'Default Light+'];
const PORT = Number(process.env.SHOOT_PORT || 9333);
const settingsFile = path.join(os.homedir(), '.cache', 'editor-comfort-shoot', 'User', 'settings.json');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`, { timeout: 10000 });
let page;
for (const c of browser.contexts()) for (const p of c.pages()) if (!page && await p.locator('.monaco-workbench').count().catch(() => 0)) page = p;
if (!page) { console.error('没找到截图实例的工作台页面(先开 node tools/shoot.mjs --serve)'); process.exit(1); }
const read = () => page.evaluate(() => {
  const wb = document.querySelector('.monaco-workbench');
  const st = getComputedStyle(wb);
  const names = new Set();
  for (const sh of document.styleSheets) { try { for (const r of sh.cssRules) if (r.style) for (let i = 0; i < r.style.length; i++) if (r.style[i].startsWith('--vscode-')) names.add(r.style[i]); } catch {} }
  for (let i = 0; i < wb.style.length; i++) if (wb.style[i].startsWith('--vscode-')) names.add(wb.style[i]);
  const out = {};
  for (const n of names) { const v = st.getPropertyValue(n).trim(); if (/^#[0-9a-f]{3,8}$|^rgba?\(/i.test(v)) out[n.slice(9).replace(/-/g, '.')] = v; }
  return out;
});
const settings = JSON.parse(fs.readFileSync(settingsFile, 'utf8'));
const result = {};
for (const id of themes) {
  const before = (await read())['editor.background'];
  fs.writeFileSync(settingsFile, JSON.stringify({ ...settings, 'workbench.colorTheme': id }, null, 1));
  // 等主题生效: 编辑区底色变化, 或最多 6 秒(连续两个主题底色相同时靠超时)
  for (let i = 0; i < 30; i++) { await sleep(200); if ((await read())['editor.background'] !== before) break; }
  await sleep(800);
  result[id] = await read();
  console.log(`${id}: ${Object.keys(result[id]).length} 个颜色键, editor.background ${result[id]['editor.background']}`);
}
fs.mkdirSync(path.dirname(path.resolve(outArg)), { recursive: true });
fs.writeFileSync(outArg, JSON.stringify(result, null, 1));
await browser.close();
