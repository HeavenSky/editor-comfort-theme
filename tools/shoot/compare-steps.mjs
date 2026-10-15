// 调色开关对比: 按 全关 / 部分开(默认) / 全开 的 COMFORT_STEPS(见 tools/gen/steps.py)分别生成主题并截图, 输出一页静态 html 对比.
// 每档截图存到 <输出目录>/<标签>_<档>/(如 new_close, new_part; 档: close 全关, part 部分开, open 全开), 标签区分改造前后的批次,
// 页面会列出输出目录里全部 <标签>_<档> 目录供勾选. 各档主题生成到 <输出目录>/_themes/<标签>_<档>/(gen_vscode.py --out), 不改 themes/;
// 截图交给 tools/shoot/shoot.mjs 一个任务拍完(场景 -> 档 -> 主题), 拍某档时该档主题临时装进 themes/, 任务结束还原.
// 先开 node tools/shoot/shoot.mjs --serve 常驻, 省掉每次启动 VS Code 与搭布局的时间.
// 用法: node tools/shoot/compare-steps.mjs <输出目录> [--all | 主题名过滤...] [--tag new] [--sets close,part] [--html]
//   过滤默认 one-dark one-light; --all: 全部主题; --tag: 本批标签(默认 new); --sets: 本批拍哪几档(默认 close,part);
//   --html: 不生成不截图, 只用输出目录里已有的图重建 index.html(秒级)
// 页面: 顶部勾选 1~3 个档按列对比(记在浏览器本地); 点图放大(Esc 或点击关闭); 鼠标停在图上按住 Option / Alt 临时显示下一个已选档,
//   按住 Ctrl 显示上一个, 松开恢复; 放大视图里同样可用
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const argv = process.argv.slice(2);
const opt = (name, def) => (argv.includes(name) ? argv[argv.indexOf(name) + 1] : def);
const htmlOnly = argv.includes('--html');
const all = argv.includes('--all');
const tag = opt('--tag', 'new');
const SETS = { close: { title: '全关', steps: 'none' }, part: { title: '部分开', steps: '' }, open: { title: '全开', steps: 'all' } };
const sets = opt('--sets', 'close,part').split(',').filter((s) => SETS[s]);
const valued = new Set(['--tag', '--sets'].map((n) => argv.indexOf(n) + 1).filter((i) => i > 0));
const [outArg, ...filters] = argv.filter((a, i) => !a.startsWith('--') && !valued.has(i));
if (!outArg) {
  console.error('用法: node tools/shoot/compare-steps.mjs <输出目录> [--all | 主题名过滤...] [--tag new] [--sets close,part] [--html]');
  process.exit(2);
}
const out = path.resolve(outArg);
const only = all ? [] : filters.length ? filters : ['one-dark', 'one-light'];
const TAGS = { old: '改造前', new: '改造后' };

const run = (cmd, args, env = {}) => {
  const r = spawnSync(cmd, args, { cwd: REPO, env: { ...process.env, ...env }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] });
  if (r.status !== 0) {
    console.error(`${cmd} ${args.join(' ')} 失败`);
    process.exit(1);
  }
  return r.stdout;
};
const runAsync = (cmd, args, env = {}) => new Promise((res, rej) => {
  const p = spawn(cmd, args, { cwd: REPO, env: { ...process.env, ...env }, stdio: ['ignore', 'ignore', 'inherit'] });
  p.on('exit', (code) => (code === 0 ? res() : rej(new Error(`${cmd} ${args.join(' ')} 失败`))));
});

fs.mkdirSync(out, { recursive: true });
if (!htmlOnly) {
  const dirs = sets.map((s) => ({ s, key: `${tag}_${s}` }));
  console.log('== 生成', dirs.map((d) => d.key).join(', '));
  await Promise.all(dirs.map(({ s, key }) => runAsync('uv', ['run', '-q', 'tools/gen/gen_vscode.py', '--out', path.join(out, '_themes', key)], { COMFORT_STEPS: SETS[s].steps })));
  // 每档的步骤开关清单留在该档目录, 页面上展示
  for (const { s, key } of dirs) {
    fs.mkdirSync(path.join(out, key), { recursive: true });
    fs.writeFileSync(path.join(out, key, 'steps.txt'), run('uv', ['run', '-q', 'tools/gen/steps.py'], { COMFORT_STEPS: SETS[s].steps }));
  }
  const job = path.join(out, '_themes', `job-${tag}.json`);
  fs.writeFileSync(job, JSON.stringify({ sets: dirs.map(({ key }) => ({ dir: path.join(out, key), src: path.join(out, '_themes', key) })), filter: only, jpg: true }));
  console.log('== 截图');
  const r = spawnSync('node', ['tools/shoot/shoot.mjs', '--job', job], { cwd: REPO, stdio: 'inherit' });
  if (r.status !== 0) process.exit(1);
}

// ======== 页面 ========
const order = ['one', 'ayu', 'sunlit', 'github', 'dracula', 'owl', 'moka', 'pale'];
const rank = (f) => { const i = order.indexOf(f.split('-')[0]); return i < 0 ? order.length : i; };
const setOrder = ['close', 'part', 'open'];
const found = fs.readdirSync(out).filter((d) => /^[a-z0-9]+_(close|part|open)$/.test(d) && fs.statSync(path.join(out, d)).isDirectory())
  .map((key) => {
    const [t, s] = key.split('_');
    const files = fs.readdirSync(path.join(out, key)).filter((f) => f.endsWith('.jpg') && (!only.length || only.some((o) => f.includes(o))));
    const steps = fs.existsSync(path.join(out, key, 'steps.txt')) ? fs.readFileSync(path.join(out, key, 'steps.txt'), 'utf8') : '';
    return { key, title: `${TAGS[t] || t} ${SETS[s].title}`, tag: t, files, steps };
  })
  .filter((x) => x.files.length)
  .sort((a, b) => (a.tag === b.tag ? 0 : a.tag === 'old' ? -1 : b.tag === 'old' ? 1 : a.tag.localeCompare(b.tag))
    || setOrder.indexOf(a.key.split('_')[1]) - setOrder.indexOf(b.key.split('_')[1]));
const shots = [...new Set(found.flatMap((x) => x.files))].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
const stamp = run('date', ['+%Y-%m-%d %H:%M:%S']).trim();
const data = { sets: found.map(({ key, title, files, steps }) => ({ key, title, files, steps })), shots };
const script = `
const D = ${JSON.stringify(data)};
const has = Object.fromEntries(D.sets.map((s) => [s.key, new Set(s.files)]));
const title = Object.fromEntries(D.sets.map((s) => [s.key, s.title]));
const keys = D.sets.map((s) => s.key);
const STORE = 'compare-steps-selected';
let sel = (JSON.parse(localStorage.getItem(STORE) || 'null') || keys.filter((k) => k.startsWith('new_')).slice(0, 3)).filter((k) => keys.includes(k));
if (!sel.length) sel = keys.slice(0, Math.min(3, keys.length));
const picker = document.getElementById('picker'), grid = document.getElementById('grid');
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
function drawPicker() {
  picker.innerHTML = D.sets.map((s) => '<label class="pick"><input type="checkbox" value="' + s.key + '"' + (sel.includes(s.key) ? ' checked' : '')
    + (!sel.includes(s.key) && sel.length >= 3 ? ' disabled' : '') + '> ' + esc(s.title) + ' <small>' + s.key + '</small>'
    + (s.steps ? '<details><summary>步骤开关</summary><pre>' + esc(s.steps) + '</pre></details>' : '') + '</label>').join('')
    + '<span class="hint">选 1~3 个; 按住 Option 看下一列, Ctrl 看上一列, 松开恢复; 点图放大</span>';
}
picker.addEventListener('change', (e) => {
  const k = e.target.value;
  if (e.target.checked) sel = keys.filter((x) => sel.includes(x) || x === k).slice(0, 3);
  else if (sel.length > 1) sel = sel.filter((x) => x !== k);
  localStorage.setItem(STORE, JSON.stringify(sel));
  drawPicker(); drawGrid();
});
const cell = (k, f) => has[k].has(f) ? '<figure data-shot="' + f + '" data-key="' + k + '"><img src="' + k + '/' + f + '" loading="lazy"><figcaption>' + esc(title[k]) + '</figcaption></figure>' : '<figure class="miss">' + esc(title[k]) + ': 无此图</figure>';
function drawGrid() {
  grid.style.setProperty('--n', sel.length);
  grid.innerHTML = D.shots.filter((f) => sel.some((k) => has[k].has(f))).map((f) => '<h2>' + f.replace(/\\.jpg$/, '') + '</h2><div class="row">' + sel.map((k) => cell(k, f)).join('') + '</div>').join('');
}
drawPicker(); drawGrid();
// 放大与按住修饰键临时换档: 在已选的档之间轮换(只选了一个时在全部档之间), 跳过缺图的档
const box = document.getElementById('box'), big = box.querySelector('img'), cap = box.querySelector('figcaption');
let hover = null, cur = null, held = null;
const ring = () => (sel.length > 1 ? sel : keys);
const step = (f, k, d) => { const r = ring(), i = Math.max(0, r.indexOf(k)); for (let n = 1; n <= r.length; n++) { const j = r[(i + d * n + r.length * n) % r.length]; if (has[j].has(f)) return j; } return k; };
const show = (f, k, tip) => { if (!tip) cur = { f, k }; big.src = k + '/' + f; cap.textContent = title[k] + (tip ? '(按住 ' + tip + ' 中)' : '') + ' · ' + f.replace(/\\.jpg$/, '') + '  (按住 Option 下一列, Ctrl 上一列, Esc 关闭)'; box.hidden = false; };
const set = (fig, k, tip) => { fig.querySelector('img').src = k + '/' + fig.dataset.shot; fig.querySelector('figcaption').textContent = title[k] + (tip ? '(按住 ' + tip + ' 中)' : ''); };
document.addEventListener('mouseover', (e) => { hover = e.target.closest('figure[data-shot]'); });
document.addEventListener('click', (e) => {
  if (e.target.closest('#picker')) return;
  if (!box.hidden) { box.hidden = true; return; }
  const f = e.target.closest('figure[data-shot]');
  if (f) show(f.dataset.shot, f.dataset.key);
});
const PEEK = { Alt: [1, 'Option'], Control: [-1, 'Ctrl'] };
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') box.hidden = true;
  if (e.repeat || held || !PEEK[e.key]) return;
  e.preventDefault();
  const [d, tip] = PEEK[e.key];
  if (!box.hidden) { held = { key: e.key }; show(cur.f, step(cur.f, cur.k, d), tip); }
  else if (hover) { held = { key: e.key, fig: hover }; set(hover, step(hover.dataset.shot, hover.dataset.key, d), tip); }
});
document.addEventListener('keyup', (e) => {
  if (!held || e.key !== held.key) return;
  e.preventDefault();
  if (held.fig) set(held.fig, held.fig.dataset.key); else if (!box.hidden) show(cur.f, cur.k);
  held = null;
});
// 切走窗口时收不到 keyup, 一样恢复
window.addEventListener('blur', () => held && document.dispatchEvent(new KeyboardEvent('keyup', { key: held.key })));
`;
fs.writeFileSync(path.join(out, 'index.html'), `<!doctype html><meta charset="utf-8"><title>调色开关对比</title>
<style>body{margin:0;font:13px -apple-system,sans-serif;background:#888}
header{position:sticky;top:0;background:#ddd;padding:6px 8px;z-index:1;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:flex-start}
.pick{background:#fff;border-radius:4px;padding:3px 8px}.pick small{color:#888}.hint{color:#555;align-self:center}
pre{max-height:60vh;overflow:auto;font-size:11px;background:#fff;margin:4px 0;position:absolute}
.row{display:grid;grid-template-columns:repeat(var(--n),1fr);gap:6px;padding:0 6px}h2{font-size:13px;margin:12px 6px 4px;color:#fff}
figure{margin:0;position:relative;cursor:zoom-in}img{width:100%;height:auto;display:block}
figcaption{position:absolute;left:0;top:0;background:#000a;color:#fff;padding:1px 6px;font-size:12px}.miss{color:#fff;padding:20px;cursor:default}
#box{position:fixed;inset:0;background:#000d;z-index:2;display:flex;align-items:center;justify-content:center;cursor:zoom-out}#box[hidden]{display:none}
#box img{max-width:98vw;max-height:94vh;width:auto}#box figcaption{top:auto;bottom:8px;left:50%;transform:translateX(-50%);font-size:14px;padding:4px 10px}</style>
<header id="picker"></header>
<p style="margin:6px;color:#fff">生成于 ${stamp}</p>
<main id="grid"></main>
<figure id="box" hidden><img><figcaption></figcaption></figure>
<script>${script}</script>
`);
console.log(`对比页: ${path.join(out, 'index.html')}(${found.map((x) => x.key).join(', ')})`);
