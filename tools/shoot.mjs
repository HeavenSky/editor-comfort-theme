// 全主题窗口截图: 启动一个独立的 VS Code 实例(独立用户目录, 从本仓库直接加载扩展, 不碰日常使用的 VS Code), 经 CDP 逐个主题截图.
// 工作区由 tools/samples/ 现建成一个 git 仓库, 带已修改 / 未跟踪 / 已删除 / 被忽略的文件和一个类型错误, 让文件树 git 着色,
// 源代码管理与问题的计数徽标都显示出来. 每个主题三张:
//   <主题>-a.png  资源管理器 + Markdown | Less + 问题面板
//   <主题>-b.png  源代码管理 + TypeScript(错误波浪线) | Python + 终端 16 色矩阵(terminal/terminal-preview.sh)
//   <主题>-c.png  搜索视图(聚焦的搜索框与未聚焦的包含 / 排除框) + 输出面板(筛选框, 通道下拉框)
// 截图期间屏幕上会出现一个 VS Code 窗口, 不要操作它. 依赖 devDependencies 里的 playwright-core.
// --thumb: 另在 <输出目录>/thumb 生成 1024 宽的 jpg 缩略图; --jpg: 原图压缩成 1600 宽的 jpg(README 用, media/screenshots; 需要 uv), 不留 png 与工作区
// 用法: node tools/shoot.mjs <输出目录> [--thumb] [--jpg] [主题名过滤...]   (VS Code 位置: 环境变量 VSCODE_APP; 调试端口: SHOOT_PORT, 默认 9333)
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { chromium } from 'playwright-core';

const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const APP = process.env.VSCODE_APP || '/Applications/Visual Studio Code.app';
const CODE = path.join(APP, 'Contents/MacOS/Code');
const PORT = Number(process.env.SHOOT_PORT || 9333);
const args = process.argv.slice(2);
const thumb = args.includes('--thumb');
const jpg = args.includes('--jpg');
const [outArg, ...only] = args.filter((a) => a !== '--thumb' && a !== '--jpg');
if (!outArg) {
  console.error('用法: node tools/shoot.mjs <输出目录> [--thumb] [--jpg] [主题名过滤...]');
  process.exit(2);
}
const out = path.resolve(outArg);
// 工作区放在输出目录下的 .work; VS Code 的配置目录要短(其 IPC socket 路径不能超过 103 字节), 固定放在 ~/.cache 下. 两者每次重建, 不残留上次的窗口布局
const work = path.join(out, '.work');
const profile = path.join(os.homedir(), '.cache', 'editor-comfort-shoot');
fs.rmSync(profile, { recursive: true, force: true });
const settingsFile = path.join(profile, 'User', 'settings.json');
const ws = path.join(work, 'workspace');
fs.rmSync(work, { recursive: true, force: true });
fs.mkdirSync(path.dirname(settingsFile), { recursive: true });
fs.mkdirSync(path.join(ws, 'src'), { recursive: true });

// 工作区: 提交一版后再制造各种 git 状态
const git = (...a) => spawnSync('git', ['-c', 'user.name=demo', '-c', 'user.email=demo@example.com', ...a], { cwd: ws });
for (const f of fs.readdirSync(path.join(REPO, 'tools/samples'))) fs.copyFileSync(path.join(REPO, 'tools/samples', f), path.join(ws, 'src', f));
fs.writeFileSync(path.join(ws, 'package.json'), '{ "name": "theme-demo", "version": "1.0.0", "private": true }\n');
fs.writeFileSync(path.join(ws, '.gitignore'), 'node_modules/\n*.log\n');
fs.writeFileSync(path.join(ws, 'README.md'), '# Theme demo\n');
git('init', '-q');
git('add', '-A');
git('commit', '-qm', 'init');
fs.appendFileSync(path.join(ws, 'src/sample.ts'), '\nexport const broken: number = "not a number";\n');
fs.appendFileSync(path.join(ws, 'src/sample.md'), '\n- 新增的一行\n');
fs.writeFileSync(path.join(ws, 'src/new-file.js'), 'console.log("new")\n');
fs.writeFileSync(path.join(ws, 'debug.log'), 'debug\n');
git('rm', '-q', 'README.md');

const pkg = JSON.parse(fs.readFileSync(path.join(REPO, 'package.json'), 'utf8'));
const themes = pkg.contributes.themes.map((t) => t.label).filter((l) => !only.length || only.some((o) => l.toLowerCase().includes(o.toLowerCase())));

const base = {
  'workbench.startupEditor': 'none', 'workbench.tips.enabled': false, 'telemetry.telemetryLevel': 'off', 'update.mode': 'none',
  'security.workspace.trust.enabled': false, 'extensions.ignoreRecommendations': true, 'window.restoreWindows': 'none',
  'git.openRepositoryInParentFolders': 'never', 'git.autoRepositoryDetection': true, 'workbench.enableExperiments': false,
  'chat.commandCenter.enabled': false, 'workbench.secondarySideBar.defaultVisibility': 'hidden', 'chat.disableAIFeatures': true,
  'editor.minimap.enabled': true, 'editor.fontSize': 13, 'window.zoomLevel': 0, 'files.exclude': {}, 'explorer.decorations.badges': true,
  'workbench.editor.enablePreview': false, 'terminal.integrated.enablePersistentSessions': false,
};
// 切换主题只改设置文件, VS Code 监听到后立即应用
const writeSettings = (theme) => fs.writeFileSync(settingsFile, JSON.stringify({ ...base, 'workbench.colorTheme': theme }, null, 1));
// 启动时扩展的主题还没注册, 设成它会被回退到默认主题, 之后写同样的值也不再触发切换; 先用内置主题, 每次截图前的写入都是真切换
writeSettings('Default Dark Modern');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const proc = spawn(CODE, [ws, '--user-data-dir', profile, '--extensions-dir', path.join(work, 'extensions'), `--extensionDevelopmentPath=${REPO}`,
  `--remote-debugging-port=${PORT}`, '--disable-workspace-trust', '--skip-welcome', '--skip-release-notes', '--new-window',
  path.join(ws, 'src/sample.md')], { stdio: 'ignore', detached: false });

let browser;
for (let i = 0; i < 60 && !browser; i++) {
  await sleep(1000);
  try { browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`); } catch {}
}
if (!browser) { console.error('连不上 VS Code 的调试端口'); proc.kill(); process.exit(1); }

const findPage = async () => {
  for (let i = 0; i < 60; i++) {
    for (const c of browser.contexts()) for (const p of c.pages()) {
      if (await p.locator('.monaco-workbench').count().catch(() => 0)) return p;
    }
    await sleep(1000);
  }
  throw new Error('没找到工作台页面');
};
const page = await findPage();
await page.waitForSelector('.monaco-workbench .part.editor', { timeout: 60000 });
await sleep(6000);

const mod = process.platform === 'darwin' ? 'Meta' : 'Control';
const command = async (label) => {
  await page.keyboard.press(`${mod}+Shift+P`);
  await page.waitForSelector('.quick-input-widget:not([style*="display: none"]) input', { timeout: 10000 });
  await page.keyboard.type(label, { delay: 5 });
  await sleep(600);
  await page.keyboard.press('Enter');
  await sleep(1200);
};

const open = async (group, file) => {
  await page.keyboard.press(`${mod}+${group === 'First' ? 1 : 2}`);
  await sleep(400);
  await page.keyboard.press(`${mod}+P`);
  await sleep(500);
  await page.keyboard.type(file, { delay: 5 });
  await sleep(900);
  await page.keyboard.press('Enter');
  await sleep(1200);
};
const shootAll = async (tag) => {
  for (const theme of themes) {
    writeSettings(theme);
    await sleep(2500);
    const file = path.join(out, `${theme.replace(/\s+/g, '-').toLowerCase()}-${tag}.png`);
    await page.screenshot({ path: file });
    console.log('截图', theme, tag);
  }
};

// A: 资源管理器(文件树 git 着色) + Markdown | Less + 问题面板
await command('View: Split Editor Right');
await open('Second', 'style.less');
await open('Second', 'sample.ts');
await open('Second', 'style.less');
await command('View: Show Explorer');
await command('View: Toggle Problems');
await sleep(4000);
await shootAll('a');

// B: 源代码管理 + TypeScript(错误波浪线) | Python + 终端 16 色矩阵
await open('Second', 'sample.py');
await open('First', 'sample.ts');
await command('View: Show Source Control');
await command('Terminal: Create New Terminal');
await sleep(2500);
await page.keyboard.type(`clear; bash '${path.join(REPO, 'terminal/terminal-preview.sh')}'`, { delay: 2 });
await page.keyboard.press('Enter');
await sleep(2500);
await shootAll('b');

// C: 搜索视图(聚焦的搜索框 vs 未聚焦的包含 / 排除框) + 输出面板(筛选框, 通道下拉框)
await command('Output: Focus on Output View');
await sleep(1500);
await command('Search: Find in Files');
await page.keyboard.type('LIMIT', { delay: 5 });
await page.keyboard.press(`${mod}+Shift+F`);
await sleep(2500);
await shootAll('c');

await browser.close().catch(() => {});
proc.kill();
if (thumb) {
  // 1024 宽的 jpg 缩略图, 便于批量目视或交给看图工具; 依赖 macOS 自带的 sips
  const dir = path.join(out, 'thumb');
  fs.mkdirSync(dir, { recursive: true });
  for (const f of fs.readdirSync(out).filter((f) => f.endsWith('.png'))) {
    spawnSync('sips', ['-s', 'format', 'jpeg', '-s', 'formatOptions', '70', '-Z', '1024', path.join(out, f), '--out', path.join(dir, f.replace(/\.png$/, '.jpg'))]);
  }
  console.log('缩略图 ->', dir);
}
if (jpg) {
  // 压缩: 缩到 1600 宽(Lanczos), jpg 质量 75 + 优化霍夫曼表 + 渐进式, 每张约 100KB(sips 质量 82 约 230KB), 文字仍清晰; 经 uv 调 Pillow
  const py = `import sys, os
from PIL import Image
for f in sys.argv[1:]:
    im = Image.open(f).convert('RGB')
    im.thumbnail((1600, 1600), Image.LANCZOS)
    im.save(f[:-4] + '.jpg', quality=75, optimize=True, progressive=True)
    os.remove(f)`;
  const pngs = fs.readdirSync(out).filter((f) => f.endsWith('.png')).map((f) => path.join(out, f));
  const r = spawnSync('uv', ['run', '-q', '--with', 'pillow', 'python', '-c', py, ...pngs], { stdio: 'inherit' });
  if (r.status !== 0) { console.error('压缩截图失败(需要 uv)'); process.exit(1); }
  fs.rmSync(work, { recursive: true, force: true });
  console.log('jpg ->', out);
}
