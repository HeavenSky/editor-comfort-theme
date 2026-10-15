// 看不清 / 刺眼排查: 按当前代码生成 全关(new_close) 与 部分开(new_part) 两档主题, 逐个主题交给 tools/shoot/shoot.mjs 截图,
// 每张截图后由 tools/lab/audit-dom.mjs 在同一画面上查按钮, 文字, 徽标, 边框, 高亮等看不清与太刺眼的位置, 记来源颜色键并截局部图.
// 每查完一个主题就重建一次 <输出目录>/index.html, 不等全部主题; 页面在检查进行中每 20 秒自动刷新(保留筛选, 滚动位置与评审标记).
// 修复建议: <输出目录>/fixes.json(子代理研究后写入)存在时, 页面在对应问题旁画出 原色 -> 建议色 的色块.
// 先开 node tools/shoot/shoot.mjs --serve 常驻, 省掉每个主题重启 VS Code 的时间.
// 用法: node tools/lab/audit-legibility.mjs <输出目录> [--all | 主题名...] [--html]
//   主题默认全部; --html: 不生成不截图, 只用已有结果重建页面
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const argv = process.argv.slice(2);
const htmlOnly = argv.includes('--html');
const [outArg, ...filters] = argv.filter((a) => !a.startsWith('--'));
if (!outArg) {
  console.error('用法: node tools/lab/audit-legibility.mjs <输出目录> [--all | 主题名...] [--html]');
  process.exit(2);
}
const out = path.resolve(outArg);
const SETS = { new_close: { title: '全关', steps: 'none' }, new_part: { title: '部分开', steps: '' } };
const order = ['one', 'ayu', 'sunlit', 'github', 'dracula', 'owl', 'moka', 'pale'];
const rank = (f) => { const i = order.indexOf(f.split('-')[0]); return i < 0 ? order.length : i; };
const allThemes = JSON.parse(fs.readFileSync(path.join(REPO, 'package.json'), 'utf8')).contributes.themes
  .map((t) => ({ label: t.label, file: path.basename(t.path, '.json') }))
  .sort((a, b) => rank(a.file) - rank(b.file) || a.file.localeCompare(b.file));
const themes = allThemes.filter((t) => !filters.length || filters.some((f) => t.file.includes(f)));

const runAsync = (cmd, args, env = {}) => new Promise((res, rej) => {
  const p = spawn(cmd, args, { cwd: REPO, env: { ...process.env, ...env }, stdio: ['ignore', 'inherit', 'inherit'] });
  p.on('exit', (code) => (code === 0 ? res() : rej(new Error(`${cmd} ${args.join(' ')} 失败`))));
});
const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; } };
const progressFile = path.join(out, 'progress.json');

// ======== 页面 ========
function build() {
  const progress = readJson(progressFile) || { done: [], total: allThemes.length, running: false };
  const fixes = readJson(path.join(out, 'fixes.json')) || {};
  const issues = new Map();
  const keyInfo = {};
  for (const t of allThemes) {
    const orig = readJson(path.join(REPO, 'assets/source', `${t.file}.json`));
    if (!orig) continue;
    const per = Object.fromEntries(Object.keys(SETS).map((s) => [s, readJson(path.join(out, '_themes', s, `${t.file}.json`))?.colors || {}]));
    const info = (k) => {
      const o = orig.colors?.[k], c = per.new_close[k], p = per.new_part[k];
      const origin = o !== undefined ? '原主题' : c !== undefined ? '补全' : p !== undefined ? '调色步骤新增' : '未定义(VS Code 默认)';
      const changed = c !== undefined && p !== undefined && c.toUpperCase() !== p.toUpperCase();
      return { orig: o, close: c, part: p, origin: origin + (changed ? ', 部分开已改' : '') };
    };
    for (const s of Object.keys(SETS)) {
      for (const scene of ['a', 'b', 'c']) {
        const name = `${t.file}-${scene}`;
        const r = readJson(path.join(out, s, 'audit', `${name}.json`));
        if (!r) continue;
        for (const it of r.items) {
          // 两档按 种类 + 来源键 + 位置 对齐(颜色在两档间可能不同)
          // 来源键与颜色在两档间可能不同, 只按位置与文字对齐; 同一档里撞号的加序号
          const base = [t.file, scene, it.kind, it.path, it.line || (it.texts || [])[0] || ''].join('|');
          let id = base, n = 1;
          while (issues.get(id)?.sets[s]) id = `${base}#${++n}`;
          if (!issues.has(id)) issues.set(id, { id, theme: t.file, label: t.label, scene, kind: it.kind, path: it.path, sets: {} });
          const g = issues.get(id);
          g.sets[s] = { ...it, crop: it.crop && `${s}/audit/${it.crop}`, shot: `${s}/${name}.jpg` };
          for (const k of [...it.fgSrc.keys, ...it.bgSrc.keys]) keyInfo[`${t.file}|${k}`] ||= info(k);
        }
      }
    }
  }
  const sev = { 看不清: 0, 刺眼: 1, 偏淡: 2, 偏刺眼: 3 };
  const list = [...issues.values()].map((g) => {
    const c = g.sets.new_close, p = g.sets.new_part;
    g.status = c && p ? '两档都有' : c ? '仅全关(部分开已修好)' : '仅部分开(调色引入)';
    g.level = (p || c).level;
    g.fix = fixes[g.id] || null;
    return g;
  }).sort((a, b) => rank(a.theme) - rank(b.theme) || a.theme.localeCompare(b.theme) || sev[a.level] - sev[b.level] || a.scene.localeCompare(b.scene));
  // 给修复研究用的精简清单(不含局部图以外的大字段)
  fs.writeFileSync(path.join(out, 'issues.json'), JSON.stringify(list.map(({ id, theme, scene, kind, path: p, status, level, sets }) => ({
    id, theme, scene, kind, path: p, status, level,
    sets: Object.fromEntries(Object.entries(sets).map(([k, v]) => [k, { level: v.level, ratio: v.ratio, fg: v.fg, bg: v.bg, fgRaw: v.fgRaw, opacity: v.opacity,
      fgKeys: v.fgSrc.keys, fgHow: v.fgSrc.how, bgKeys: v.bgSrc.keys, count: v.count, texts: v.texts, crop: v.crop }])),
    keys: Object.fromEntries([...new Set(Object.values(sets).flatMap((v) => [...v.fgSrc.keys, ...v.bgSrc.keys]))].map((k) => [k, keyInfo[`${theme}|${k}`]])),
  })), null, 1));
  const stamp = spawnSync('date', ['+%Y-%m-%d %H:%M:%S'], { encoding: 'utf8' }).stdout.trim();
  const data = { issues: list, keyInfo, progress, stamp, themes: allThemes.map((t) => t.file), fixCount: Object.keys(fixes).length };
  fs.writeFileSync(path.join(out, 'index.html'), PAGE(data));
}

const PAGE = (data) => `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>看不清 / 刺眼排查</title>
<style>
body{margin:0;font:13px/1.5 -apple-system,"PingFang SC",sans-serif;background:#1b1d22;color:#ddd}
header{position:sticky;top:0;z-index:10;background:#24272e;padding:8px 14px;border-bottom:1px solid #3a3e48;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center}
header b{color:#fff} header select,header input{background:#30343c;color:#ddd;border:1px solid #4a4f5a;border-radius:4px;padding:2px 6px}
.cnt{color:#9aa} .run{color:#f5c26b}
main{padding:10px 14px}
h2{margin:22px 0 8px;color:#fff;font-size:16px;border-bottom:1px solid #3a3e48;padding-bottom:4px}
.card{background:#24272e;border:1px solid #353944;border-radius:6px;margin:10px 0;padding:10px;display:grid;grid-template-columns:1fr 1fr 330px;gap:10px}
.card.ok{opacity:.45} .card.yes{border-color:#d9534f} .card.later{border-color:#e0a030}
.col h4{margin:0 0 4px;font-size:12px;color:#9ab}
.col img{max-width:100%;max-height:260px;display:block;border:1px solid #444;cursor:zoom-in;background:#000}
.none{color:#6a6;font-size:12px;padding:20px 0}
.lv{display:inline-block;padding:0 6px;border-radius:3px;font-size:12px;color:#fff}
.lv-看不清{background:#c0392b}.lv-偏淡{background:#8e6d2b}.lv-刺眼{background:#a0309a}.lv-偏刺眼{background:#6a3d7a}
.meta{font-size:12px;color:#aab;word-break:break-all} .meta code{color:#e6c07b}
.sw{display:inline-block;width:14px;height:14px;border:1px solid #888;vertical-align:-3px;position:relative;cursor:pointer;margin:0 2px}
.sw:hover::after{content:attr(data-hex);position:absolute;z-index:20;left:20px;top:-46px;width:110px;height:110px;background:inherit;border:2px solid #fff;
 box-shadow:0 4px 16px #000a;color:#fff;font:12px monospace;display:flex;align-items:flex-end;padding:3px;box-sizing:border-box;text-shadow:0 0 3px #000,0 0 3px #000}
.arrow{color:#888;margin:0 2px}
.fix{background:#1f2f24;border:1px solid #2f5a3a;border-radius:4px;padding:6px;margin-top:6px;font-size:12px}
.rv button{background:#30343c;color:#ddd;border:1px solid #4a4f5a;border-radius:4px;padding:1px 8px;margin-right:4px;cursor:pointer}
.rv button.on{background:#4a6fa5;color:#fff}
.rv textarea{width:100%;box-sizing:border-box;background:#1b1d22;color:#ddd;border:1px solid #444;margin-top:4px;height:38px}
#zoom{position:fixed;inset:0;background:#000d;display:none;z-index:50;align-items:center;justify-content:center}
#zoom img{max-width:96vw;max-height:94vh}
</style></head><body>
<header>
 <b>看不清 / 刺眼排查</b>
 <span class="cnt" id="prog"></span>
 <label>主题 <select id="fTheme"><option value="">全部</option></select></label>
 <label>级别 <select id="fLevel"><option value="">全部</option><option>看不清</option><option>偏淡</option><option>刺眼</option><option>偏刺眼</option></select></label>
 <label>种类 <select id="fKind"><option value="">全部</option></select></label>
 <label>两档 <select id="fStatus"><option value="">全部</option><option>两档都有</option><option>仅全关(部分开已修好)</option><option>仅部分开(调色引入)</option></select></label>
 <label>评审 <select id="fRv"><option value="">全部</option><option value="none">未标</option><option value="yes">是问题</option><option value="ok">不是问题</option><option value="later">待定</option></select></label>
 <input id="fText" placeholder="搜键名 / 文字 / 位置">
 <span class="cnt" id="shown"></span>
 <button id="export">导出评审 json</button>
</header>
<main id="main"></main>
<div id="zoom"><img></div>
<script>
const D = ${JSON.stringify(data).replace(/</g, '\\u003c')};
const SC = { a: 'a 资源管理器 + Markdown | Less + 问题', b: 'b 源代码管理 + TS | Python + 终端', c: 'c 搜索 + 输出' };
const LS = 'audit-legibility:' + location.pathname;
const st = JSON.parse(localStorage.getItem(LS) || '{}');
st.rv ||= {}; st.f ||= {};
const save = () => localStorage.setItem(LS, JSON.stringify(st));
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sw = (h) => h ? '<span class="sw" style="background:' + esc(h.length === 9 ? h : h) + '" data-hex="' + esc(h) + '"></span>' : '';
const p = D.progress;
document.getElementById('prog').innerHTML = '已查 ' + p.done.length + ' / ' + p.total + ' 个主题' + (p.running ? ' <span class="run">检查进行中, 每 20 秒自动刷新</span>' : '') +
  ' · 生成于 ' + D.stamp + (D.fixCount ? ' · 修复建议 ' + D.fixCount + ' 条' : '');
for (const t of D.themes) document.getElementById('fTheme').insertAdjacentHTML('beforeend', '<option>' + t + '</option>');
for (const k of [...new Set(D.issues.map((i) => i.kind))].sort()) document.getElementById('fKind').insertAdjacentHTML('beforeend', '<option>' + esc(k) + '</option>');
const keys = (theme, src) => (src?.keys || []).map((k) => {
  const i = D.keyInfo[theme + '|' + k] || {};
  return '<code>' + esc(k) + '</code> <span title="原主题 / 全关 / 部分开">' + sw(i.orig) + sw(i.close) + sw(i.part) + '</span> <i>' + esc(i.origin || '') + '</i>';
}).join('<br>') + (src?.how === 'value' ? ' <i>(按颜色值反查, 可能不唯一)</i>' : src?.how === 'none' ? '<i>来源未匹配到颜色键</i>' : '');
const col = (g, s, title) => {
  const it = g.sets[s];
  if (!it) return '<div class="col"><h4>' + title + '</h4><div class="none">这一档没有此问题</div></div>';
  return '<div class="col"><h4>' + title + ' <span class="lv lv-' + it.level + '">' + it.level + '</span> 对比度 ' + it.ratio + (it.count > 1 ? ' · 同类 ' + it.count + ' 处' : '') +
    ' · <a href="' + it.shot + '" target="_blank" style="color:#7ab">整张</a></h4>' +
    (it.crop ? '<img loading="lazy" src="' + it.crop + '">' : '') +
    '<div class="meta">前景 ' + sw(it.fg) + esc(it.fg) + (it.fgRaw && it.fgRaw !== it.fg ? ' (原值 ' + esc(it.fgRaw) + (it.opacity < 1 ? ', 透明度 ' + it.opacity : '') + ')' : '') + ' 来源:<br>' + keys(g.theme, it.fgSrc) +
    '<br>底色 ' + sw(it.bg) + esc(it.bg) + (it.bgSrc?.keys?.length ? ' 来源:<br>' + keys(g.theme, it.bgSrc) : '') +
    (it.texts?.length ? '<br>文字: ' + esc(it.texts.join(' / ')) : '') + '</div></div>';
};
const fixHtml = (f) => !f ? '' : '<div class="fix"><b>修复建议</b> ' + esc(f.direction || '') + '<br>' + (f.changes || []).map((c) =>
  '<code>' + esc(c.key) + '</code> ' + sw(c.from) + esc(c.from) + '<span class="arrow">→</span>' + sw(c.to) + esc(c.to) + (c.ratio ? ' (对比度 ' + esc(c.ratio) + ')' : '')).join('<br>') +
  (f.note ? '<br>' + esc(f.note) : '') + '</div>';
function render() {
  const f = st.f, q = (f.text || '').toLowerCase();
  const list = D.issues.filter((g) => (!f.theme || g.theme === f.theme) && (!f.level || g.level === f.level) && (!f.kind || g.kind === f.kind) &&
    (!f.status || g.status === f.status) && (!f.rv || (f.rv === 'none' ? !st.rv[g.id]?.v : st.rv[g.id]?.v === f.rv)) &&
    (!q || JSON.stringify(g).toLowerCase().includes(q)));
  document.getElementById('shown').textContent = '显示 ' + list.length + ' / ' + D.issues.length;
  let html = '', last = '';
  for (const g of list) {
    if (g.theme !== last) { last = g.theme; html += '<h2>' + esc(g.label || g.theme) + ' <span class="cnt">' + g.theme + '</span></h2>'; }
    const r = st.rv[g.id] || {};
    html += '<div class="card ' + (r.v || '') + '" data-id="' + esc(g.id) + '">' + col(g, 'new_close', '全关 new_close') + col(g, 'new_part', '部分开 new_part') +
      '<div class="meta"><b style="color:#fff">' + esc(g.kind) + '</b> <span class="lv lv-' + g.level + '">' + g.level + '</span><br>' + esc(g.status) + '<br>场景 ' + esc(SC[g.scene]) +
      '<br>位置 <code>' + esc(g.path) + '</code>' + fixHtml(g.fix) +
      '<div class="rv" style="margin-top:8px">' + [['yes', '是问题'], ['ok', '不是问题'], ['later', '待定']].map(([v, t]) => '<button data-v="' + v + '" class="' + (r.v === v ? 'on' : '') + '">' + t + '</button>').join('') +
      '<textarea placeholder="备注(期望改成什么样)">' + esc(r.note || '') + '</textarea></div></div></div>';
  }
  document.getElementById('main').innerHTML = html || '<p>没有符合条件的问题</p>';
}
for (const [id, k] of [['fTheme', 'theme'], ['fLevel', 'level'], ['fKind', 'kind'], ['fStatus', 'status'], ['fRv', 'rv'], ['fText', 'text']]) {
  const el = document.getElementById(id);
  el.value = st.f[k] || '';
  el.addEventListener('input', () => { st.f[k] = el.value; save(); render(); });
}
document.getElementById('main').addEventListener('click', (e) => {
  const b = e.target.closest('.rv button');
  if (b) {
    const id = b.closest('.card').dataset.id;
    const r = st.rv[id] ||= {};
    r.v = r.v === b.dataset.v ? '' : b.dataset.v;
    save(); render(); return;
  }
  if (e.target.tagName === 'IMG') { const z = document.getElementById('zoom'); z.querySelector('img').src = e.target.src; z.style.display = 'flex'; }
});
document.getElementById('main').addEventListener('change', (e) => {
  if (e.target.tagName !== 'TEXTAREA') return;
  const id = e.target.closest('.card').dataset.id;
  (st.rv[id] ||= {}).note = e.target.value; save();
});
document.getElementById('zoom').onclick = () => { document.getElementById('zoom').style.display = 'none'; };
addEventListener('keydown', (e) => { if (e.key === 'Escape') document.getElementById('zoom').style.display = 'none'; });
document.getElementById('export').onclick = () => {
  const outj = Object.entries(st.rv).filter(([, r]) => r.v || r.note).map(([id, r]) => ({ id, review: r.v || '', note: r.note || '' }));
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(outj, null, 1)], { type: 'application/json' }));
  a.download = 'review.json'; a.click();
};
render();
scrollTo(0, st.scroll || 0);
addEventListener('scroll', () => { st.scroll = scrollY; save(); });
// 检查进行中自动刷新; 正在写备注时推迟
if (p.running) setInterval(() => { if (document.activeElement?.tagName !== 'TEXTAREA') location.reload(); }, 20000);
</script></body></html>`;

// ======== 流程 ========
fs.mkdirSync(out, { recursive: true });
if (htmlOnly) {
  build();
  console.log(`已重建 ${path.join(out, 'index.html')}`);
  process.exit(0);
}
console.log('== 补全段与两档主题');
await runAsync('uv', ['run', '-q', 'tools/gen/complete.py']);
await Promise.all(Object.entries(SETS).map(([s, v]) => runAsync('uv', ['run', '-q', 'tools/gen/gen_vscode.py', '--out', path.join(out, '_themes', s)], { COMFORT_STEPS: v.steps })));
// 进度按全部主题计: 之前查过而这次不重查的主题仍算已查
const prev = readJson(progressFile)?.done || [];
const progress = { done: prev.filter((f) => !themes.some((t) => t.file === f)), total: allThemes.length, running: true };
fs.writeFileSync(progressFile, JSON.stringify(progress));
build();
console.log(`页面: ${path.join(out, 'index.html')}`);
for (const t of themes) {
  const job = path.join(out, '_themes', `job-${t.file}.json`);
  fs.writeFileSync(job, JSON.stringify({
    sets: Object.keys(SETS).map((s) => ({ dir: path.join(out, s), src: path.join(out, '_themes', s) })),
    filter: [t.file], jpg: true, audit: path.join(REPO, 'tools/lab/audit-dom.mjs'),
  }));
  console.log(`== ${t.label}`);
  const r = spawnSync('node', ['tools/shoot/shoot.mjs', '--job', job], { cwd: REPO, stdio: 'inherit' });
  if (r.status !== 0) { console.error(`${t.label} 截图或检查失败, 跳过`); continue; }
  progress.done.push(t.file);
  fs.writeFileSync(progressFile, JSON.stringify(progress));
  build();
  console.log(`已更新页面(${progress.done.length}/${allThemes.length})`);
}
progress.running = false;
fs.writeFileSync(progressFile, JSON.stringify(progress));
build();
console.log(`完成: ${path.join(out, 'index.html')}`);
