// 全主题窗口截图: 启动一个独立的 VS Code 实例(独立用户目录, 从本仓库直接加载扩展, 不碰日常使用的 VS Code), 经 CDP 逐个主题截图.
// 工作区由 tools/samples/ 现建成一个 git 仓库, 带已修改 / 未跟踪 / 已删除 / 被忽略的文件和一个类型错误, 让文件树 git 着色,
// 源代码管理与问题的计数徽标都显示出来. 每个主题三张:
//   <主题>-a.png  资源管理器 + Markdown | Less + 问题面板
//   <主题>-b.png  源代码管理 + TypeScript(错误波浪线) | Python + 终端 16 色矩阵(tools/terminal/terminal-preview.sh)
//   <主题>-c.png  搜索视图(聚焦的搜索框与未聚焦的包含 / 排除框) + 输出面板(筛选框, 通道下拉框)
// 截图期间会出现一个 VS Code 窗口, 它在后台启动不抢焦点, 被挡住或失焦也照常截图; 只是不要在它上面点击或打字.
// 每张截图前核对主题已生效: 工作台的界面色(CSS 变量)与语法色(.mtk 样式)都要与主题文件一致, 否则报错, 不截错主题.
// 依赖 devDependencies 里的 playwright-core.
// --thumb: 另在 <输出目录>/thumb 生成 1024 宽的 jpg 缩略图; --jpg: 原图压缩成 1600 宽的 jpg(README 用, media/screenshots; 需要 uv), 不留 png
// README 用相对路径引用 media/screenshots/, 截图不进 .vsix, 打包时改写成 GitHub raw/HEAD 地址; 重拍后不提交, Marketplace 与 GitHub 页面就仍是旧图.
// 用法: node tools/shoot/shoot.mjs <输出目录> [--thumb] [--jpg] [主题名过滤...]   (VS Code 位置: 环境变量 VSCODE_APP; 调试端口: SHOOT_PORT, 默认 9333)
//       node tools/shoot/shoot.mjs --serve   常驻: 启动一次 VS Code 并保持, 在 127.0.0.1:SHOOT_CTL_PORT(默认 9334)接收截图任务, Ctrl+C 或
//                                      curl -X POST 127.0.0.1:9334/quit 退出; 常驻进程在时, 上面的单次用法与 --job 自动交给它, 省掉启动与搭布局的时间
//       node tools/shoot/shoot.mjs --job <任务.json>   任务: { "sets": [{ "dir": 输出目录, "src": 主题 json 目录(可省) }], "filter": [...], "jpg": true, "thumb": false,
//                                      "audit": 检查模块路径(可省, 如 tools/lab/audit-dom.mjs), "settings": 本任务期间叠加的 VS Code 设置(可省) }
//                                      多组按 场景 -> 组 -> 主题 的顺序拍, 每个场景的布局只搭一次; 有 src 的组拍前把该组主题临时装进 themes/, 任务结束还原
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';
import { chromium } from 'playwright-core';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const THEMES = path.join(REPO, 'themes');
const APP = process.env.VSCODE_APP || '/Applications/Visual Studio Code.app';
const CODE = path.join(APP, 'Contents/MacOS/Code');
const PORT = Number(process.env.SHOOT_PORT || 9333);
const CTL = Number(process.env.SHOOT_CTL_PORT || 9334);
// VS Code 的配置目录要短(其 IPC socket 路径不能超过 103 字节), 固定放在 ~/.cache 下; 工作区放在旁边. 两者每次启动重建, 不残留上次的窗口布局
const profile = path.join(os.homedir(), '.cache', 'editor-comfort-shoot');
const work = path.join(os.homedir(), '.cache', 'editor-comfort-shoot-work');
const ws = path.join(work, 'workspace');
const settingsFile = path.join(profile, 'User', 'settings.json');
const mac = process.platform === 'darwin';
const mod = mac ? 'Meta' : 'Control';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const base = {
  'workbench.startupEditor': 'none', 'workbench.tips.enabled': false, 'telemetry.telemetryLevel': 'off', 'update.mode': 'none',
  'security.workspace.trust.enabled': false, 'extensions.ignoreRecommendations': true, 'window.restoreWindows': 'none',
  'git.openRepositoryInParentFolders': 'never', 'git.autoRepositoryDetection': true, 'workbench.enableExperiments': false,
  'chat.commandCenter.enabled': false, 'workbench.secondarySideBar.defaultVisibility': 'hidden', 'chat.disableAIFeatures': true,
  'editor.minimap.enabled': true, 'editor.fontSize': 13, 'window.zoomLevel': 0, 'files.exclude': {}, 'explorer.decorations.badges': true,
  'workbench.editor.enablePreview': false, 'terminal.integrated.enablePersistentSessions': false,
  // 窗口不在前台时命令面板 / 快速打开不因失焦关闭
  'workbench.quickOpen.closeOnFocusLost': false,
};
// 切换主题只改设置文件, VS Code 监听到后立即应用
// 任务的 settings 只在该任务期间叠加(如普查打开空白符显示), 任务结束清掉, 不影响之后的截图
let jobSettings = {};
const writeSettings = (theme) => fs.writeFileSync(settingsFile, JSON.stringify({ ...base, ...jobSettings, 'workbench.colorTheme': theme }, null, 1));

// 切换主题按设置 ID(VS Code 取 id, 没有时取 label); 截图按主题文件名命名(themes/one-dark.json -> one-dark-a.png)
const themeList = (only = []) => JSON.parse(fs.readFileSync(path.join(REPO, 'package.json'), 'utf8')).contributes.themes
  .map((t) => ({ id: t.id || t.label, label: t.label, file: path.basename(t.path, '.json') }))
  .filter((t) => !only.length || only.some((o) => `${t.label} ${t.file}`.toLowerCase().includes(o.toLowerCase())));

// ======== 启动 ========
const shootPids = () => (spawnSync('pgrep', ['-f', '--', `--user-data-dir ${profile}`], { encoding: 'utf8' }).stdout || '').split(/\s+/).filter(Boolean);
const frontPid = () => ((spawnSync('lsappinfo', ['info', '-only', 'pid', (spawnSync('lsappinfo', ['front'], { encoding: 'utf8' }).stdout || '').trim()],
  { encoding: 'utf8' }).stdout || '').match(/pid = (\d+)/) || [])[1];
// VS Code 建窗口, 开终端时会自己激活; 前台变成截图实例时按 pid 切回之前的前台应用(两个 VS Code 同一个 bundle, 只能按 pid 区分).
// 用户自己切到别的应用时不干预. 只在启动与执行任务期间守护, 常驻空闲时不轮询
const guardFront = () => {
  const userPid = mac ? frontPid() : null;
  if (!userPid) return () => {};
  const t = setInterval(() => {
    const f = frontPid();
    if (f && f !== userPid && shootPids().includes(f)) {
      spawnSync('osascript', ['-l', 'JavaScript', '-e',
        `ObjC.import('AppKit'); $.NSRunningApplication.runningApplicationWithProcessIdentifier(${userPid}).activateWithOptions($.NSApplicationActivateAllWindows)`]);
    }
  }, 300);
  return () => clearInterval(t);
};

function makeWorkspace() {
  fs.rmSync(work, { recursive: true, force: true });
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
}

// ======== 单实例 ========
// 截图用的 VS Code 共用一个用户目录与调试端口, 同一时间只能有一个持有者(常驻进程或单次截图): 锁文件记持有者 pid, 持有者已退出的锁视为过期.
// 两个实例并存时后起的拿不到调试端口, 连上的会是先起的那个, 截图与关闭都会错位
const LOCK = path.join(os.homedir(), '.cache', 'editor-comfort-shoot.lock');
const alive = (pid) => { try { process.kill(pid, 0); return true; } catch { return false; } };
function lock() {
  for (let i = 0; i < 2; i++) {
    try {
      fs.writeFileSync(LOCK, String(process.pid), { flag: 'wx' });
      process.on('exit', () => { try { if (fs.readFileSync(LOCK, 'utf8') === String(process.pid)) fs.rmSync(LOCK); } catch {} });
      return 0;
    } catch {
      const pid = Number(fs.readFileSync(LOCK, 'utf8'));
      if (pid && pid !== process.pid && alive(pid)) return pid;
      fs.rmSync(LOCK, { force: true });
    }
  }
  return -1;
}
// 按独有的用户目录结束截图实例, 等进程真的退出; TERM 不退时 KILL
async function killShoot() {
  for (const sig of ['-TERM', '-TERM', '-KILL']) {
    if (!shootPids().length) return;
    spawnSync('pkill', [sig, '-f', '--', `--user-data-dir ${profile}`]);
    for (let i = 0; i < 25 && shootPids().length; i++) await sleep(200);
  }
}
const portBusy = () => (spawnSync('lsof', ['-nP', `-iTCP:${PORT}`, '-sTCP:LISTEN'], { encoding: 'utf8' }).stdout || '').trim() !== '';

async function launch() {
  // 上次没收干净的截图实例(持有者被强杀等)先结束; 之后调试端口仍被占就是别的程序, 报错而不是连上去
  await killShoot();
  if (portBusy()) throw new Error(`调试端口 ${PORT} 被其他程序占用(换端口: SHOOT_PORT)`);
  fs.rmSync(profile, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(settingsFile), { recursive: true });
  makeWorkspace();
  // 启动时扩展的主题还没注册, 设成它会被回退到默认主题, 之后写同样的值也不再触发切换; 先用内置主题, 每次截图前的写入都是真切换
  writeSettings('Default Dark Modern');
  // 后台 / 被遮挡的窗口不降频, 不停止绘制, 否则失焦后截到的是旧画面
  const codeArgs = [ws, '--user-data-dir', profile, '--extensions-dir', path.join(work, 'extensions'), `--extensionDevelopmentPath=${REPO}`,
    `--remote-debugging-port=${PORT}`, '--disable-workspace-trust', '--skip-welcome', '--skip-release-notes', '--new-window',
    '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--disable-background-timer-throttling'];
  const stopGuard = guardFront();
  // macOS 用 open -g -n 在后台起一个新实例, 不抢走前台焦点; 结束时按独有的用户目录找到它的进程退出
  const proc = mac ? spawnSync('open', ['-g', '-n', '-a', APP, '--args', ...codeArgs]) : spawn(CODE, codeArgs, { stdio: 'ignore' });
  const quit = async () => {
    stopGuard();
    if (mac) await killShoot(); else proc.kill();
    fs.rmSync(work, { recursive: true, force: true });
  };
  let browser;
  for (let i = 0; i < 60 && !browser; i++) {
    await sleep(1000);
    try { browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`); } catch {}
  }
  if (!browser) { await quit(); throw new Error('连不上 VS Code 的调试端口'); }
  let page;
  for (let i = 0; i < 60 && !page; i++) {
    for (const c of browser.contexts()) for (const p of c.pages()) {
      if (!page && await p.locator('.monaco-workbench').count().catch(() => 0)) page = p;
    }
    if (!page) await sleep(1000);
  }
  if (!page) { await quit(); throw new Error('没找到工作台页面'); }
  // 让页面始终认为自己有焦点: 按键经 CDP 送达, 窗口在不在前台都一样, 编辑器与输入框的焦点样式也照常显示
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Emulation.setFocusEmulationEnabled', { enabled: true });
  await page.waitForSelector('.monaco-workbench .part.editor', { timeout: 60000 });
  await sleep(6000);
  stopGuard();
  return { browser, page, terminal: false, close: async () => { await browser.close().catch(() => {}); await quit(); } };
}

// ======== 布局 ========
// 布局步骤的固定等待: 常驻进程跑完第一个任务后(文件已索引, 语言服务已就绪)减半
const WARM = 0.5;
const wait = (s, ms) => sleep(s.warm ? ms * WARM : ms);
const command = async (s, label) => {
  await s.page.keyboard.press(`${mod}+Shift+P`);
  await s.page.waitForSelector('.quick-input-widget:not([style*="display: none"]) input', { timeout: 10000 });
  await s.page.keyboard.type(label, { delay: 5 });
  await wait(s, 600);
  await s.page.keyboard.press('Enter');
  await wait(s, 1200);
};
const open = async (s, group, file) => {
  await s.page.keyboard.press(`${mod}+${group === 'First' ? 1 : 2}`);
  await wait(s, 400);
  await s.page.keyboard.press(`${mod}+P`);
  await wait(s, 500);
  await s.page.keyboard.type(file, { delay: 5 });
  await wait(s, 900);
  await s.page.keyboard.press('Enter');
  await wait(s, 1200);
};
// 每个场景都从可重复的状态搭起: 常驻时上一次任务停在场景 C, 新任务的场景 A 先关掉全部编辑器组再重新分栏
const SCENES = {
  // A: 资源管理器(文件树 git 着色) + Markdown | Less + 问题面板
  a: async (s) => {
    await command(s, 'View: Close All Editor Groups');
    await open(s, 'First', 'sample.md');
    await command(s, 'View: Split Editor Right');
    await open(s, 'Second', 'style.less');
    await open(s, 'Second', 'sample.ts');
    await open(s, 'Second', 'style.less');
    await command(s, 'View: Show Explorer');
    await command(s, 'Problems: Focus on Problems View');
    await wait(s, 4000);
  },
  // B: 源代码管理 + TypeScript(错误波浪线) | Python + 终端 16 色矩阵; 常驻时终端只建一次, 之后切回它
  b: async (s) => {
    await open(s, 'Second', 'sample.py');
    await open(s, 'First', 'sample.ts');
    await command(s, 'View: Show Source Control');
    if (s.terminal) {
      await command(s, 'Terminal: Focus Terminal');
      await wait(s, 1500);
      return;
    }
    await command(s, 'Terminal: Create New Terminal');
    await wait(s, 2500);
    await s.page.keyboard.type(`clear; bash '${path.join(REPO, 'tools/terminal/terminal-preview.sh')}'`, { delay: 2 });
    await s.page.keyboard.press('Enter');
    await wait(s, 2500);
    s.terminal = true;
  },
  // C: 搜索视图(聚焦的搜索框 vs 未聚焦的包含 / 排除框) + 输出面板(筛选框, 通道下拉框); 搜索框原有的字被选中, 重打不累加
  c: async (s) => {
    await command(s, 'Output: Focus on Output View');
    await wait(s, 1500);
    await command(s, 'Search: Find in Files');
    await s.page.keyboard.type('LIMIT', { delay: 5 });
    await s.page.keyboard.press(`${mod}+Shift+F`);
    await wait(s, 2500);
  },
};

// ======== 主题生效核对 ========
// 不透明界面色对应工作台的 CSS 变量(--vscode-<键, 点换横线>; 半透明色变量里是 rgba 写法, 不比), 语法色对应编辑器的 .mtkN 样式
const expectOf = (file) => {
  const t = JSON.parse(fs.readFileSync(file, 'utf8'));
  const hex6 = (v) => typeof v === 'string' && /^#[0-9a-f]{6}$/i.test(v);
  return {
    colors: Object.fromEntries(Object.entries(t.colors).filter(([, v]) => hex6(v)).map(([k, v]) => [k, v.toLowerCase()])),
    toks: [...new Set(t.tokenColors.map((r) => r.settings?.foreground).filter(hex6).map((v) => v.toLowerCase()))],
  };
};
const mismatch = (page, exp) => page.evaluate(({ colors, toks }) => {
  const st = getComputedStyle(document.querySelector('.monaco-workbench'));
  const bad = Object.entries(colors).filter(([k, v]) => {
    const got = st.getPropertyValue('--vscode-' + k.replace(/\./g, '-')).trim().toLowerCase();
    return got && got !== v;
  }).map(([k]) => k);
  const css = [...document.querySelectorAll('style')].map((x) => x.textContent).filter((x) => x.includes('.mtk')).join('\n');
  const have = new Set((css.match(/\.mtk\d+\s*\{\s*color:\s*#[0-9a-f]{6}/gi) || []).map((m) => m.slice(-7).toLowerCase()));
  return { bad, miss: toks.filter((x) => !have.has(x)) };
}, exp);

async function apply(s, theme) {
  const file = path.join(THEMES, `${theme.file}.json`);
  const exp = expectOf(file);
  writeSettings(theme.id);
  let r;
  for (let i = 0; i < 60; i++) {
    await sleep(200);
    r = await mismatch(s.page, exp);
    if (!r.bad.length && !r.miss.length) return;
    // 同一主题换了一组颜色(组间切换, 或此前加载过的旧内容被缓存): 重写主题文件, 让开发模式下的主题文件监听重新加载当前主题
    if (i === 10 || i === 30) fs.writeFileSync(file, fs.readFileSync(file));
  }
  throw new Error(`主题 ${theme.id} 没有生效: 界面色 ${r.bad.length} 处不符(如 ${r.bad.slice(0, 3).join(', ')}), 语法色缺 ${r.miss.length} 个`);
}

// ======== 任务 ========
function compress(dir, thumb, jpg) {
  const pngs = fs.readdirSync(dir).filter((f) => f.endsWith('.png'));
  if (thumb) {
    // 1024 宽的 jpg 缩略图, 便于批量目视或交给看图工具; 依赖 macOS 自带的 sips
    const t = path.join(dir, 'thumb');
    fs.mkdirSync(t, { recursive: true });
    for (const f of pngs) spawnSync('sips', ['-s', 'format', 'jpeg', '-s', 'formatOptions', '70', '-Z', '1024', path.join(dir, f), '--out', path.join(t, f.replace(/\.png$/, '.jpg'))]);
  }
  if (jpg && pngs.length) {
    // 压缩: 缩到 1600 宽(Lanczos), jpg 质量 75 + 优化霍夫曼表 + 渐进式, 每张约 100KB(sips 质量 82 约 230KB), 文字仍清晰; 经 uv 调 Pillow
    const py = `import sys, os
from PIL import Image
for f in sys.argv[1:]:
    im = Image.open(f).convert('RGB')
    im.thumbnail((1600, 1600), Image.LANCZOS)
    im.save(f[:-4] + '.jpg', quality=75, optimize=True, progressive=True)
    os.remove(f)`;
    const r = spawnSync('uv', ['run', '-q', '--with', 'pillow', 'python', '-c', py, ...pngs.map((f) => path.join(dir, f))], { stdio: 'inherit' });
    if (r.status !== 0) throw new Error('压缩截图失败(需要 uv)');
  }
}

async function runJob(s, job, log) {
  const themes = themeList(job.filter || []);
  const sets = job.sets.map((x) => ({ ...x, dir: path.resolve(x.dir), src: x.src && path.resolve(x.src) }));
  const saved = Object.fromEntries(themes.map((t) => [t.file, fs.readFileSync(path.join(THEMES, `${t.file}.json`))]));
  // job.audit: 检查模块路径(导出 audit(page, ctx)), 每张截图后在同一画面上调用; 每次任务重新加载, 常驻进程不用重启
  const audit = job.audit ? (await import(`${pathToFileURL(path.resolve(job.audit)).href}?t=${Date.now()}`)).audit : null;
  jobSettings = job.settings || {};
  const stopGuard = guardFront();
  const t0 = Date.now();
  try {
    for (const x of sets) fs.mkdirSync(x.dir, { recursive: true });
    for (const [tag, setup] of Object.entries(SCENES)) {
      await setup(s);
      for (const x of sets) {
        for (const t of themes) {
          if (x.src) fs.copyFileSync(path.join(x.src, `${t.file}.json`), path.join(THEMES, `${t.file}.json`));
          await apply(s, t);
          await sleep(600);
          await s.page.screenshot({ path: path.join(x.dir, `${t.file}-${tag}.png`) });
          log(`截图 ${t.label} ${tag} -> ${path.basename(x.dir)}`);
          if (audit) await audit(s.page, { dir: x.dir, name: `${t.file}-${tag}`, theme: t.file, scene: tag, log });
        }
      }
    }
  } finally {
    jobSettings = {};
    stopGuard();
    for (const [f, buf] of Object.entries(saved)) {
      const p = path.join(THEMES, `${f}.json`);
      if (!fs.readFileSync(p).equals(buf)) fs.writeFileSync(p, buf);
    }
  }
  s.warm = true;
  for (const x of sets) compress(x.dir, job.thumb, job.jpg);
  log(`完成 ${themes.length} 个主题 x ${sets.length} 组 x 3 场景, 用时 ${Math.round((Date.now() - t0) / 1000)} 秒`);
}

// ======== 常驻与客户端 ========
const ping = () => new Promise((res) => {
  const r = http.get({ host: '127.0.0.1', port: CTL, path: '/ping', timeout: 500 }, (x) => { x.resume(); res(x.statusCode === 200); });
  r.on('error', () => res(false));
  r.on('timeout', () => { r.destroy(); res(false); });
});
// 任务交给常驻进程: 日志逐行转到本进程输出, 最后一行 OK / ERROR 决定退出码
const remote = (job) => new Promise((res) => {
  const body = JSON.stringify(job);
  const r = http.request({ host: '127.0.0.1', port: CTL, path: '/job', method: 'POST', headers: { 'content-type': 'application/json' } }, (x) => {
    let last = '';
    x.setEncoding('utf8');
    x.on('data', (d) => { process.stdout.write(d); last = (last + d).split('\n').filter(Boolean).pop() || last; });
    x.on('end', () => res(last.startsWith('OK') ? 0 : 1));
  });
  r.on('error', (e) => { console.error('常驻截图进程连接失败:', e.message); res(1); });
  r.end(body);
});

async function serve() {
  if (await ping()) { console.error(`常驻截图进程已在 127.0.0.1:${CTL} 运行`); process.exit(1); }
  const holder = lock();
  if (holder) { console.error(`另一个截图进程正在运行(pid ${holder}), 不再启动常驻`); process.exit(1); }
  const s = await launch();
  let closing = false;
  const bye = async (code = 0) => { closing = true; await s.close(); process.exit(code); };
  // 截图用的 VS Code 窗口被关掉时常驻进程跟着退出, 免得接了任务却没有窗口可拍
  s.browser.on('disconnected', () => { if (closing) return; console.error('VS Code 已退出, 常驻截图结束'); process.exit(1); });
  process.on('SIGINT', () => bye());
  process.on('SIGTERM', () => bye());
  let queue = Promise.resolve();
  http.createServer((req, res) => {
    if (req.url === '/ping') return res.end('ok');
    if (req.url === '/quit') { res.end('bye\n'); return bye(); }
    if (req.url !== '/job' || req.method !== 'POST') { res.statusCode = 404; return res.end(); }
    let body = '';
    req.on('data', (d) => { body += d; });
    req.on('end', () => {
      res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
      const log = (line) => { res.write(line + '\n'); console.log(line); };
      queue = queue.then(() => runJob(s, JSON.parse(body), log))
        .then(() => res.end('OK\n'), (e) => { console.error(e.message); res.end(`ERROR ${e.message}\n`); });
    });
  }).listen(CTL, '127.0.0.1', () => console.log(`常驻截图已就绪: 127.0.0.1:${CTL}(VS Code 调试端口 ${PORT})`));
}

const args = process.argv.slice(2);
if (args.includes('--serve')) {
  await serve();
} else {
  let job;
  if (args.includes('--job')) {
    job = JSON.parse(fs.readFileSync(args[args.indexOf('--job') + 1], 'utf8'));
  } else {
    const [outArg, ...only] = args.filter((a) => a !== '--thumb' && a !== '--jpg');
    if (!outArg) {
      console.error('用法: node tools/shoot/shoot.mjs <输出目录> [--thumb] [--jpg] [主题名过滤...] | --serve | --job <任务.json>');
      process.exit(2);
    }
    job = { sets: [{ dir: outArg }], filter: only, jpg: args.includes('--jpg'), thumb: args.includes('--thumb') };
  }
  // 相对路径按本进程的工作目录解析, 交给常驻进程前先转成绝对路径
  job.sets = job.sets.map((x) => ({ ...x, dir: path.resolve(x.dir), src: x.src && path.resolve(x.src) }));
  if (await ping()) process.exit(await remote(job));
  const holder = lock();
  if (holder) { console.error(`另一个截图进程正在运行(pid ${holder}), 等它结束再拍, 或先开常驻(--serve)让任务排队`); process.exit(1); }
  const s = await launch();
  let code = 0;
  try { await runJob(s, job, console.log); } catch (e) { console.error(e.message); code = 1; }
  await s.close();
  process.exit(code);
}
