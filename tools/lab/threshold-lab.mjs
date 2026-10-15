// 门槛标定台: 普查 16 套主题全关档(原主题 + 补全, 不调色)画面上的元素, 按颜色键分层(tools/lab/key-levels.mjs, /keys 页复核)归到
// 内容 / 暗化 / 线条 / 底色 四组 x 强 / 中 / 弱 三档, 在网页上标定各级的目标与上下限, 以及区分度, 提交后作为调色步骤与门禁共用的门槛.
// 指标: 统一相对指标 = 元素与其底色的 OKLab 明度差 / 本主题正文(editor.foreground 于 editor.background)的明度差 x 100%;
//   绝对指标: 内容组与暗化强 / 中用 APCA Lc(APCA-W3 0.0.98G-4g), 暗化弱, 线条与底色组用 OKLab ΔE x 100(APCA 把 Lc 约 10 以下截成 0).
// 区分度: 同组相邻两档的相对指标之差要有最小值; 跨组同档之间要有最小区分度; 不同组不同档不设数值, 在矩阵页看视觉效果.
// 推荐值(v2, 规范锚定 + 原主题数据校准, 主题等权):
//   目标 = 各主题中位数的 20% 截尾均值; 无样本时取规范锚点, 与锚点差超过 15 个百分点时提示(多半是键归属问题).
//   依据主题默认为参考主题(用户认可的原主题, REF0), 可在页面切换为全部主题.
//   下限(修复下限, 步骤与门禁用) = 依据主题实例的 P5, 不高于混档线; 混档线(排查用) = 本级目标与梯子上弱一档目标的中点.
//   禁用状态不设下限(WCAG 惯例), 低于下限只报偏淡.
//   上限 = 与强一档目标的中点(像强一档), 梯子顶端取各主题 P90 的跨主题中位数; 刺眼上限本期不定.
//   绝对下限 = min(规范值(APCA 分级, WCAG 非文字对比, OKLab 可辨差), 依据主题实例的 P5), 显示参考 / 其他主题被它挡下的占比.
//   梯子: 前景 内容强 > 内容中 > 内容弱 > 暗化强 > 暗化中 > 暗化弱; 线条 强 > 中 > 弱; 底色 强 > 中 > 弱.
//   区分度取各主题差值掐头去尾后的 P25, 不低于 5(原主题有档位倒挂, 最小值会是负数).
// 标注: 每个实例按所在级的目标标 不及目标 / 合适 / 超出目标; 页面按标注给出上下限建议.
// 用法: node tools/lab/threshold-lab.mjs collect <输出目录> [主题名...] [--src <主题目录>]   普查(--src: 不生成全关档, 直接普查该目录的主题; 先开 node tools/shoot/shoot.mjs --serve; 普查期间打开空白符显示), 每查完一个主题页面就能看到
//       node tools/lab/threshold-lab.mjs export <输出目录> [目标文件]    把已提交的门槛, 颜色键分层与普查配对表导出成调色步骤与门禁的输入(默认 assets/levels.json)
//       node tools/lab/threshold-lab.mjs report <输出目录>                 看不清排查: 按 assets/levels.json 判定普查到的每组色对, 写 <输出目录>/report.html 与 report.json;
//                                                                    另写刺眼审查 glare.html(只列脚本拿不定的, 用 serve 打开 /glare.html 才能保存标注)
//       node tools/lab/threshold-lab.mjs serve <输出目录> [--port 9340]  打开 http://127.0.0.1:9340/ ; /keys 为颜色键分层复核, 提交写 key-levels.json;
//                                                                    标定页提交写 thresholds.json(另存带时间的副本)与 labels.json
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';
import { classify, keysData, KEYS_PAGE } from './key-levels.mjs';
import { calibrateByKeys, rulePairs } from './rule-pairs.mjs';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const [cmd, outArg, ...rest] = process.argv.slice(2);
if (!['collect', 'serve', 'export', 'report'].includes(cmd) || !outArg) {
  console.error('用法: node tools/lab/threshold-lab.mjs collect <输出目录> [主题名...] | serve <输出目录> [--port 9340]');
  process.exit(2);
}
const out = path.resolve(outArg);
const SET = 'new_close';
const order = ['one', 'ayu', 'sunlit', 'github', 'dracula', 'owl', 'moka', 'pale'];
const rank = (f) => { const i = order.indexOf(f.split('-')[0]); return i < 0 ? order.length : i; };
const allThemes = JSON.parse(fs.readFileSync(path.join(REPO, 'package.json'), 'utf8')).contributes.themes
  .map((t) => ({ label: t.label, file: path.basename(t.path, '.json') }))
  .sort((a, b) => rank(a.file) - rank(b.file) || a.file.localeCompare(b.file));
const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; } };
const stamp = (fmt) => spawnSync('date', [fmt], { encoding: 'utf8' }).stdout.trim();
fs.mkdirSync(out, { recursive: true });

// ======== 普查 ========
if (cmd === 'collect') {
  const filters = rest.filter((a, i) => !a.startsWith('--') && rest[i - 1] !== '--src');
  const themes = allThemes.filter((t) => !filters.length || filters.some((f) => t.file.includes(f)));
  const run = (c, a, env = {}) => new Promise((res, rej) => {
    const p = spawn(c, a, { cwd: REPO, env: { ...process.env, ...env }, stdio: ['ignore', 'ignore', 'inherit'] });
    p.on('exit', (code) => (code === 0 ? res() : rej(new Error(`${c} ${a.join(' ')} 失败`))));
  });
  const src = rest.includes('--src') ? path.resolve(rest[rest.indexOf('--src') + 1]) : null;
  if (src) {
    // 普查现成主题(如 themes/ 的默认档), 用于按 assets/levels.json 排查看不清; 不重新生成
    console.log(`== 复制主题 ${path.relative(REPO, src) || src}`);
    fs.mkdirSync(path.join(out, '_themes', SET), { recursive: true });
    for (const t of allThemes) fs.copyFileSync(path.join(src, `${t.file}.json`), path.join(out, '_themes', SET, `${t.file}.json`));
  } else {
    console.log('== 生成全关主题');
    await run('uv', ['run', '-q', 'tools/gen/complete.py']);
    await run('uv', ['run', '-q', 'tools/gen/gen_vscode.py', '--out', path.join(out, '_themes', SET)], { COMFORT_STEPS: 'none' });
  }
  const pf = path.join(out, 'progress.json');
  const progress = { done: (readJson(pf)?.done || []).filter((f) => !themes.some((t) => t.file === f)), total: allThemes.length, running: true };
  fs.writeFileSync(pf, JSON.stringify(progress));
  for (const t of themes) {
    const job = path.join(out, '_themes', `job-${t.file}.json`);
    fs.writeFileSync(job, JSON.stringify({ sets: [{ dir: path.join(out, SET), src: path.join(out, '_themes', SET) }], filter: [t.file], jpg: true,
      audit: path.join(REPO, 'tools/lab/census-dom.mjs'), settings: { 'editor.renderWhitespace': 'all' } }));
    console.log(`== ${t.label}`);
    const r = spawnSync('node', ['tools/shoot/shoot.mjs', '--job', job], { cwd: REPO, stdio: 'inherit' });
    if (r.status !== 0) { console.error(`${t.label} 失败, 跳过`); continue; }
    progress.done.push(t.file);
    fs.writeFileSync(pf, JSON.stringify(progress));
  }
  progress.running = false;
  fs.writeFileSync(pf, JSON.stringify(progress));
  console.log('普查完成');
  process.exit(0);
}

// ======== 数据 ========
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const lum = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
const apca = (txt, bg) => {
  const Y = (c) => 0.2126729 * (c[0] / 255) ** 2.4 + 0.7151522 * (c[1] / 255) ** 2.4 + 0.0721750 * (c[2] / 255) ** 2.4;
  const clamp = (y) => (y > 0.022 ? y : y + (0.022 - y) ** 1.414);
  const t = clamp(Y(txt)), b = clamp(Y(bg));
  if (Math.abs(b - t) < 0.0005) return 0;
  const s = b > t ? (b ** 0.56 - t ** 0.57) * 1.14 : (b ** 0.65 - t ** 0.62) * 1.14;
  return Math.abs(b > t ? (s < 0.1 ? 0 : s - 0.027) : (s > -0.1 ? 0 : s + 0.027)) * 100;
};
const oklab = (c) => {
  const [r, g, b] = c.map(lin);
  const l = Math.cbrt(0.4122214708 * r + 0.5363137080 * g + 0.0514459929 * b), m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b),
    s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
};
const dL = (a, b) => Math.abs(oklab(rgb(a))[0] - oklab(rgb(b))[0]) * 100;
const dE = (a, b) => { const x = oklab(rgb(a)), y = oklab(rgb(b)); return Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]) * 100; };
// 注释色: 主题 tokenColors 里作用域为 comment 的前景, 编辑区代码里同色的记为 注释
const themeJson = (f) => readJson(path.join(out, '_themes', SET, `${f}.json`));
const commentColor = (t) => {
  let hit = null;
  for (const r of t?.tokenColors || []) {
    const sc = Array.isArray(r.scope) ? r.scope : String(r.scope || '').split(',').map((s) => s.trim());
    if (sc.some((s) => s === 'comment' || s === 'comment.line' || s === 'comment.block') && r.settings?.foreground) hit = r.settings.foreground.slice(0, 7).toUpperCase();
  }
  return hit;
};
// 没有来源键时按普查角色兜底
const ROLE_LEVEL = {
  代码: '内容中', 注释: '暗化强', 主要文字: '内容中', 图标: '内容中', 状态栏文字: '内容弱', 次要文字: '内容弱', 非活动标签: '内容弱', 禁用: '内容弱',
  活动标签: '内容强', 当前行号: '内容强', 选中行文字: '内容强', 活动栏选中图标: '内容强', 徽标文字: '内容中', 按钮文字: '内容中',
  行号: '暗化中', 活动栏图标: '暗化中', 空白符: '暗化弱', '焦点 / 指示线': '线条强', '边框 / 分隔线': '线条弱', 高亮底: '底色中', 色块底: '底色弱', '徽标 / 按钮底': '底色强',
};
function data() {
  const kl = readJson(path.join(out, 'key-levels.json'))?.levels || {};
  const levelOfKey = (k) => kl[k] || (({ group, level }) => group + level)(classify(k));
  const themes = [];
  const items = [];
  for (const t of allThemes) {
    const tj = themeJson(t.file);
    if (!tj) continue;
    const cc = commentColor(tj);
    const fg = (tj.colors['editor.foreground'] || '#FFFFFF').slice(0, 7).toUpperCase(), bg = (tj.colors['editor.background'] || '#000000').slice(0, 7).toUpperCase();
    const body = { fg, bg, lc: +apca(rgb(fg), rgb(bg)).toFixed(1), dl: +dL(fg, bg).toFixed(1) };
    let found = false;
    for (const scene of ['a', 'b', 'c']) {
      const r = readJson(path.join(out, SET, 'census', `${t.file}-${scene}.json`));
      if (!r) continue;
      found = true;
      for (const it of r.items) {
        const role = it.role === '代码' && cc && it.fg === cc ? '注释' : it.role;
        const key = it.selfKeys?.[0];
        let level = role === '代码' ? '内容中' : role === '注释' ? '暗化强' : key ? levelOfKey(key) : ROLE_LEVEL[role] || '内容中';
        // 不在四组里(基准 / 不适用 / 未归类)的按角色兜底; 按值反查到的键与元素类型不符(细条分隔线被认成同色底色键等)时不信该键
        const roleGroup = /边框|焦点/.test(role) ? ['线条'] : /底/.test(role) ? ['底色'] : ['内容', '暗化'];
        let keyNote = '';
        // 归为不适用的键(只在拖拽时出现的插入线, 阴影等)不参与统计
        if (level === '不适用' && it.selfHow !== 'value') continue;
        if (level === '不适用') { keyNote = '反查不符'; level = ROLE_LEVEL[role] || '内容中'; }
        else if (!/^(内容|暗化|线条|底色)/.test(level)) level = ROLE_LEVEL[role] || '内容中';
        else if (it.selfHow === 'value' && !roleGroup.includes(level.slice(0, 2))) { keyNote = '反查不符'; level = ROLE_LEVEL[role] || '内容中'; }
        const d = dL(it.fg, it.bg);
        items.push({ ...it, role, theme: t.file, scene, level, keyNote, key: key || (role === '代码' || role === '注释' ? '(语法色)' : ''),
          rd: +((d / body.dl) * 100).toFixed(1), dl: +d.toFixed(1), de: +dE(it.fg, it.bg).toFixed(1),
          id: `${t.file}|${scene}|${role}|${it.fg}|${it.bg}`, crop: it.crop && `${SET}/census/${it.crop}` });
      }
    }
    // 深浅按主题文件的编辑区底色判断, 不用普查记录(旧普查把浅色误记为深色)
    if (found) themes.push({ file: t.file, label: t.label, dark: lum(rgb(bg)) < 0.2, body });
  }
  return { themes, items, progress: readJson(path.join(out, 'progress.json')), saved: readJson(path.join(out, 'thresholds.json')),
    labels: readJson(path.join(out, 'labels.json')) || {}, keyLevelsAt: readJson(path.join(out, 'key-levels.json'))?.at || null };
}

// 按颜色值反查到的底色键是一串同色候选, 第一个可能是别处的同色键(如 Pale Light 侧栏底被认成 inputValidation.infoBackground, 而它在本主题里是深蓝),
// 从候选里优先挑常见的真实界面底色
const SURFACES = ['editor.background', 'editorGutter.background', 'editorGroupHeader.tabsBackground', 'tab.activeBackground', 'tab.inactiveBackground', 'breadcrumb.background',
  'sideBar.background', 'sideBarSectionHeader.background', 'sideBarTitle.background', 'panel.background', 'activityBar.background', 'statusBar.background',
  'titleBar.activeBackground', 'commandCenter.background', 'editorWidget.background', 'list.activeSelectionBackground', 'list.inactiveSelectionBackground',
  'list.focusBackground', 'list.hoverBackground', 'button.background', 'badge.background', 'activityBarBadge.background', 'input.background', 'dropdown.background'];
const pickUnder = (it) => {
  const us = it.underKeys || [];
  if (it.underHow !== 'value' || us.length < 2) return us[0];
  return SURFACES.find((x) => us.includes(x)) || us[0];
};

// ======== 导出 ========
// levels.json: levels(各级门槛, 来自 thresholds.json), keyLevels(颜色键 -> 级, 复核结果优先), pairs(颜色键 -> 普查实测画在其上的底色键, 按出现次数排序)
if (cmd === 'export') {
  const th = readJson(path.join(out, 'thresholds.json'));
  if (!th) { console.error('标定目录里没有 thresholds.json(先在标定台提交)'); process.exit(1); }
  const kl = readJson(path.join(out, 'key-levels.json'))?.levels || {};
  const registry = readJson(path.join(REPO, 'assets/vscode/color-registry.json')).colors;
  const keys = new Set(Object.keys(registry).filter((k) => !registry[k].deprecated));
  for (const t of allThemes) for (const k of Object.keys(readJson(path.join(REPO, 'assets/source', `${t.file}.json`))?.colors || {})) keys.add(k);
  const keyLevels = Object.fromEntries([...keys].sort().map((k) => [k, kl[k] || (({ group, level }) => group + level)(classify(k))]));
  const cnt = {};
  for (const it of data().items) {
    const k = it.selfKeys?.[0], u = pickUnder(it);
    if (!k || !u || k === u || it.keyNote || !keyLevels[k] || !/^(内容|暗化|线条|底色)/.test(keyLevels[k])) continue;
    ((cnt[k] ||= {})[u] = (cnt[k][u] || 0) + 1);
  }
  // 只留出现次数不低于最常见底色键 30% 的: 其余多是按颜色值反查到的同色键, 不是真正画在其上的底色
  const pairs = Object.fromEntries(Object.entries(cnt).sort().map(([k, v]) => {
    const s = Object.entries(v).sort((a, b) => b[1] - a[1]);
    return [k, s.filter(([, n]) => n >= s[0][1] * 0.3).map(([u]) => u)];
  }));
  // 刺眼线(宽口径, 只拦参考主题里也少见的): 参考主题实例(同主题同角色同色对合并)的 P95; 明度差看 rd, 底色与线条另看彩度超出所在底色的量(OKLCH 彩度差 x 100, 整套偏色的底如 Solarized 不算)
  const q95 = (v) => { if (!v.length) return null; const x = [...v].sort((a, b) => a - b), i = (x.length - 1) * 0.95, j = Math.floor(i); return +(x[j] + (x[Math.min(j + 1, x.length - 1)] - x[j]) * (i - j)).toFixed(1); };
  const chroma = (c) => { const [, a, b] = oklab(rgb(c)); return Math.hypot(a, b) * 100; };
  const censusItems = data().items, refInst = new Map();
  // 只用来源键可靠的实例: 无键按角色兜底, 按值反查的会把指示线(如面板标签下的激活线)归成弱档, 把 P95 拉到离谱; 刺眼线不低于上限 hi
  for (const it of censusItems) {
    if (!(th.ref || []).includes(it.theme) || !it.key || it.keyNote || it.selfHow === 'value') continue;
    refInst.set(`${it.theme}|${it.role}|${it.fg}|${it.bg}`, it);
  }
  const glare = (k, hi) => {
    const v = [...refInst.values()].filter((x) => x.level === k), rd = q95(v.map((x) => x.rd));
    return { rd: rd == null ? null : Math.max(rd, hi ?? 0), chroma: /^(线条|底色)/.test(k) ? q95(v.map((x) => Math.max(0, chroma(x.fg) - chroma(x.bg)))) : null, n: v.length };
  };
  const levels = Object.fromEntries(Object.entries(th.levels).map(([k, v]) => [k, { pct: v.pct, lo: v.lo, mixLo: v.mixLo, hi: v.hi, abs: v.abs, abs_metric: /^(内容|暗化强|暗化中)/.test(k) ? 'apca' : 'de', glare: glare(k, v.hi), source: 'census' }]));
  // 普查覆盖不到的键(截图场景之外的界面)按语义规则推配对底色键(tools/lab/rule-pairs.mjs); 普查配对优先
  const four = Object.keys(keyLevels).filter((k) => /^(内容|暗化|线条|底色)/.test(keyLevels[k]) && !pairs[k]);
  const ruled = rulePairs(four, new Set(Object.keys(registry)), (k) => keyLevels[k]);
  const pairsFrom = Object.fromEntries([...Object.keys(pairs).map((k) => [k, 'census']), ...Object.keys(ruled).map((k) => [k, 'rule'])].sort());
  Object.assign(pairs, ruled);
  // 普查样本为 0 的级按参考主题的颜色键取值标定: 键值(半透明的叠在配对底色上)对配对底色的 rd 与 ΔE; 相邻级的混档线与上限随之重算
  const LADDERS = [['内容强', '内容中', '内容弱', '暗化强', '暗化中', '暗化弱'], ['线条强', '线条中', '线条弱'], ['底色强', '底色中', '底色弱']];
  const ABS_SPEC = { 线条中: 10 };
  const mid = (a, b) => +((a + b) / 2).toFixed(1);
  for (const [k, lv] of Object.entries(levels)) {
    if (censusItems.some((x) => x.level === k && (th.ref || []).includes(x.theme))) continue;
    const samples = [];
    for (const t of (th.ref || [])) {
      const tj = themeJson(t);
      if (!tj) continue;
      const c = tj.colors, body = dL((c['editor.foreground'] || '#FFFFFF').slice(0, 7), (c['editor.background'] || '#000000').slice(0, 7));
      for (const [key, l] of Object.entries(keyLevels)) {
        if (l !== k || !/^#[0-9A-Fa-f]{6,8}$/.test(c[key] || '') || !pairs[key]) continue;
        const u = (c[pairs[key][0]] || c['editor.background']).slice(0, 7), a = c[key].length === 9 ? parseInt(c[key].slice(7), 16) / 255 : 1;
        const fg = '#' + rgb(c[key]).map((x, i) => Math.round(x * a + rgb(u)[i] * (1 - a)).toString(16).padStart(2, '0')).join('');
        if (dE(fg, u) < 1) continue;
        samples.push({ theme: t, rd: (dL(fg, u) / body) * 100, abs: dE(fg, u) });
      }
    }
    const cal = calibrateByKeys(samples, ABS_SPEC[k] ?? lv.abs);
    if (!cal) continue;
    const lad = LADDERS.find((x) => x.includes(k)), i = lad.indexOf(k), up = levels[lad[i - 1]], dn = levels[lad[i + 1]];
    Object.assign(lv, { pct: cal.pct, abs: cal.abs, source: `keys(${cal.n} 个实例, ${cal.themes} 套参考主题)` });
    lv.mixLo = dn ? mid(lv.pct, dn.pct) : lv.mixLo;
    lv.hi = up ? mid(lv.pct, up.pct) : lv.hi;
    lv.lo = Math.min(cal.lo, lv.mixLo ?? cal.lo);
    if (up) { up.mixLo = mid(up.pct, lv.pct); up.lo = Math.min(up.lo, up.mixLo); }
    if (dn) dn.hi = mid(dn.pct, lv.pct);
    console.log(`${k} 按颜色键标定: 目标 ${lv.pct}, 修复下限 ${lv.lo}, 绝对下限 ${lv.abs}, 混档线 ${lv.mixLo}, 上限 ${lv.hi} (${lv.source})`);
  }
  const doc = { about: '分层门槛(tools/lab/threshold-lab.mjs export 生成, 勿手改): 相对指标 rd = OKLab 明度差 / 本主题正文明度差 x 100; 绝对指标 apca = APCA Lc, de = OKLab ΔE x 100',
    thresholdsAt: th.at, ref: th.ref, levels, sep: th.sep, rules: th.rules, exemptSameColor: 'focus|selection|findMatch|Cursor', keyLevels, pairs, pairsFrom };
  const dest = path.resolve(rest[0] || path.join(REPO, 'assets/levels.json'));
  fs.writeFileSync(dest, JSON.stringify(doc, null, 1) + '\n');
  console.log(`已导出 ${path.relative(REPO, dest)}: ${Object.keys(levels).length} 级, ${Object.keys(keyLevels).length} 个键, ${Object.keys(pairs).length} 个键有配对(普查 ${Object.keys(pairs).length - Object.keys(ruled).length}, 规则 ${Object.keys(ruled).length})`);
  process.exit(0);
}

// ======== 排查报告 ========
// 按 assets/levels.json(调色步骤与门禁的同一份门槛)判定普查到的每组色对:
//   不及目标 = 相对指标低于修复下限或绝对指标低于绝对下限(禁用不判, 底色弱只报告); 刺眼 = 高于 levels.json 的刺眼线 glare(明度差 rd, 底色与线条另看比底色多出的彩度; 只判来源键可靠的实例); 偏淡 = 低于混档线(像弱一档); 偏重 = 高于上限(像强一档).
//   线条与底色弱同色(ΔE < 1)按原设计不画豁免, 焦点框 / 选区 / 当前匹配不豁免.
// 另给出 level_floor 为什么没管到它(终端键, 语法色, 主题未定义, 无实测配对, 实测底色与配对底色不同), 用来判断是补配对, 补步骤还是确实不用修.
// 区分度与相对约束也在这里按普查实例报告(口径同标定台); 不放进 metrics.py: 按颜色键近似测不准, 会把参考主题大面积误报.
if (cmd === 'report') {
  const L = readJson(path.join(REPO, 'assets/levels.json'));
  const refs = new Set(L.ref);
  const { themes, items } = data();
  const bodyOf = Object.fromEntries(themes.map((t) => [t.file, t.body]));
  // 键值叠在实测底色上应画出的颜色; 与实测字色不同说明界面另加了透明度(禁用, 非活动的工具栏按钮等), 改键值管不到
  // 刺眼只判来源键可靠的实例(口径同 export 标定刺眼线): 无键或按值反查的级别可能归错
  const reliable = (it) => it.key && !it.keyNote && it.selfHow !== 'value';
  const fgChroma = (c) => { const [, a, b] = oklab(rgb(c)); return Math.hypot(a, b) * 100; };
  const drawn = (v, bg) => {
    const a = v.length === 9 ? parseInt(v.slice(7), 16) / 255 : 1, c = rgb(v), b = rgb(bg);
    return '#' + c.map((x, i) => Math.round(x * a + b[i] * (1 - a)).toString(16).padStart(2, '0')).join('').toUpperCase();
  };
  const rows = [];
  for (const it of items) {
    const lv = L.levels[it.level];
    if (!lv) continue;
    const body = bodyOf[it.theme];
    const ab = +(lv.abs_metric === 'apca' ? apca(rgb(it.fg), rgb(it.bg)) : dE(it.fg, it.bg)).toFixed(1);
    const disabled = it.role === '禁用' || /disabled/i.test(it.key);
    if ((/^线条/.test(it.level) || it.level === '底色弱') && it.de < 1 && !new RegExp(L.exemptSameColor, 'i').test(it.key)) continue;
    let verdict = null;
    if (!disabled && (it.rd < lv.lo - 0.05 || ab < lv.abs - 0.05)) verdict = '不及目标';
    else if (reliable(it) && ((lv.glare?.rd != null && it.rd > lv.glare.rd + 0.05) || (lv.glare?.chroma != null && fgChroma(it.fg) - fgChroma(it.bg) > lv.glare.chroma + 0.05))) verdict = '刺眼';
    else if (lv.mixLo != null && it.rd < lv.mixLo - 0.05) verdict = '偏淡';
    else if (lv.hi != null && it.rd > lv.hi + 0.05) verdict = '偏重';
    if (!verdict) continue;
    const colors = themeJson(it.theme)?.colors || {};
    const k = it.key, u = pickUnder(it), pair = L.pairs[k];
    const why = it.level === '底色弱' ? '底色弱只报告' : disabled ? '禁用不设下限' : k.startsWith('terminal.') ? '终端键(终端步骤负责)'
      : k === '(语法色)' ? '语法色(语法步骤负责)' : !k ? '无来源键' : it.keyNote ? '来源键不可信(按值反查不符)'
      : !colors[k] ? '主题未定义(VS Code 推导)' : drawn(colors[k], it.bg) !== it.fg && dE(drawn(colors[k], it.bg), it.fg) > 1 ? `渲染色与键值 ${colors[k]} 不同(界面另加透明度)`
      : !pair ? '无实测配对' : u && !pair.includes(u) ? `实测底色 ${u} 不在配对 ${pair.join(', ')}` : '有配对(按配对底色已达标)';
    rows.push({ theme: it.theme, ref: refs.has(it.theme), scene: it.scene, role: it.role, level: it.level, key: k, under: u || '', fg: it.fg, bg: it.bg,
      rd: it.rd, ab, metric: lv.abs_metric, lo: lv.lo, abs: lv.abs, mixLo: lv.mixLo, hi: lv.hi, verdict, why, count: it.count || 1,
      text: (it.texts || []).slice(0, 2).join(' / ').slice(0, 60), crop: it.crop || '', shot: `${SET}/${it.theme}-${it.scene}.jpg` });
  }
  // 区分度与相对约束(只报告): 口径同标定台 pairs() / cells() / rulesPage(): 同主题同角色同色对跨场景合并, 线条与底色弱同色的不计; 每级取 rd 中位数
  const medOf = (v) => { if (!v.length) return null; const x = [...v].sort((a, b) => a - b), n = x.length; return n % 2 ? x[(n - 1) / 2] : (x[n / 2 - 1] + x[n / 2]) / 2; };
  const uniq = new Map();
  for (const it of items) {
    if (it.de < 1 && (/^线条/.test(it.level) || it.level === '底色弱') && !new RegExp(L.exemptSameColor, 'i').test(it.key || '')) continue;
    uniq.set(`${it.theme}|${it.role}|${it.fg}|${it.bg}`, it);
  }
  const rel = {};
  for (const t of themes) {
    const P = [...uniq.values()].filter((x) => x.theme === t.file), out = [];
    const M = (k) => medOf(P.filter((x) => x.level === k).map((x) => x.rd));
    for (const [k, lo] of Object.entries(L.sep?.inGroup || {})) {
      const x = M(k.slice(0, 2) + k[2]), y = M(k.slice(0, 2) + k[4]);
      if (lo != null && x != null && y != null && x - y < lo - 0.05) out.push(`区分度 ${k} ${(x - y).toFixed(1)} < ${lo}`);
    }
    for (const [k, lo] of Object.entries(L.sep?.cross || {})) {
      const [a, b] = k.split('|'), x = M(a), y = M(b);
      if (lo != null && x != null && y != null && Math.abs(x - y) < lo - 0.05) out.push(`区分度 ${k} ${Math.abs(x - y).toFixed(1)} < ${lo}`);
    }
    for (const r of L.rules || []) {
      const x = medOf(P.filter((p) => p.role === r.a).map((p) => p.rd)), y = medOf(P.filter((p) => p.role === r.b).map((p) => p.rd));
      if (x != null && y && !(r.min - 0.005 <= x / y && x / y <= r.max + 0.005)) out.push(`相对约束 ${r.a}/${r.b} ${(x / y).toFixed(2)} 不在 [${r.min}, ${r.max}]`);
    }
    rel[t.file] = out;
  }
  const vo = { 不及目标: 0, 刺眼: 1, 偏淡: 2, 偏重: 3 }, VS = Object.keys(vo);
  rows.sort((a, b) => vo[a.verdict] - vo[b.verdict] || rank(a.theme) - rank(b.theme) || a.theme.localeCompare(b.theme) || a.rd - b.rd);
  const at = stamp('+%Y-%m-%d %H:%M:%S');
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify({ at, thresholdsAt: L.thresholdsAt, relations: rel, rows }, null, 1));
  const esc = (x) => String(x).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const sw = (c) => `<i style="background:${c}"></i>`;
  const tally = {};
  for (const r of rows) ((tally[r.theme] ||= Object.fromEntries(VS.map((v) => [v, 0])))[r.verdict]++);
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>看不清排查(分层门槛)</title><style>
body{font:13px/1.5 -apple-system,sans-serif;margin:16px;color:#222}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:3px 6px;vertical-align:top}
th{background:#f4f4f4;position:sticky;top:0}i{display:inline-block;width:12px;height:12px;border:1px solid #888;vertical-align:middle;margin-right:2px}
img{max-width:420px;max-height:120px}.v0{color:#c00;font-weight:600}.v1{color:#c0c;font-weight:600}.v2{color:#b70}.v3{color:#06c}.ref{background:#eef6ff}#f label{margin-right:12px}code{font-size:12px}
</style></head><body><h2>看不清排查(按 assets/levels.json, 门槛 ${esc(L.thresholdsAt)}; 生成 ${at})</h2>
<p>不及目标 = 低于修复下限或绝对下限(调色步骤与门禁的口径, 应为 0 或有原因); 刺眼 = 高于刺眼线(参考主题实例 P95 的明度差, 底色与线条另看比所在底色多出的彩度; 只判来源键可靠的; 只报告); 偏淡 = 低于混档线, 像弱一档; 偏重 = 高于上限, 像强一档. 蓝底行是参考主题. 数值: rd = 相对正文明度差 %, 绝对指标 apca = Lc, de = ΔE x 100.</p>
<table><tr><th>主题</th>${VS.map((v) => `<th>${v}</th>`).join('')}</tr>${themes.map((t) => `<tr class="${refs.has(t.file) ? 'ref' : ''}"><td>${esc(t.label)}</td>${VS.map((v) => `<td>${tally[t.file]?.[v] || 0}</td>`).join('')}</tr>`).join('')}</table>
<h3>区分度与相对约束(只报告)</h3><p>区分度: 同组相邻两档 / 跨组同档的 rd 中位数之差不低于 levels.json 的 sep(按参考主题差值的 P25 定, 参考主题约四分之一越界是预期); 相对约束: 两类角色 rd 中位数之比落在 rules 范围(按参考主题范围外放一成).</p>
<table><tr><th>主题</th><th>越界</th></tr>${themes.map((t) => `<tr class="${refs.has(t.file) ? 'ref' : ''}"><td>${esc(t.label)}</td><td>${rel[t.file].map(esc).join('<br>') || '-'}</td></tr>`).join('')}</table>
<p id="f">${VS.map((v, i) => `<label><input type="checkbox" value="${v}" ${i === 0 ? 'checked' : ''}> ${v}</label>`).join('')}
<label><input type="checkbox" id="onlyFix"> 只看 level_floor 本应管到的(有配对)</label></p>
<table id="t"><tr><th>判定</th><th>主题</th><th>场景 / 角色</th><th>级</th><th>颜色键 / 底色键</th><th>色</th><th>rd(下限 / 混档 / 上限)</th><th>绝对(下限)</th><th>level_floor</th><th>局部图</th></tr>
${rows.map((r) => `<tr data-v="${r.verdict}" data-fix="${/^有配对|^实测底色/.test(r.why) ? 1 : 0}" class="${r.ref ? 'ref' : ''}"><td class="v${vo[r.verdict]}">${r.verdict}</td><td>${esc(r.theme)}</td>
<td>${r.scene} / ${esc(r.role)}${r.text ? `<br><small>${esc(r.text)}</small>` : ''}</td><td>${r.level}</td><td><code>${esc(r.key)}</code><br><code>${esc(r.under)}</code></td>
<td>${sw(r.fg)}${r.fg}<br>${sw(r.bg)}${r.bg}</td><td>${r.rd} (${r.lo} / ${r.mixLo ?? '-'} / ${r.hi ?? '-'})</td><td>${r.metric} ${r.ab} (${r.abs})</td><td>${esc(r.why)}</td>
<td>${r.crop ? `<a href="${r.crop}" target="_blank"><img loading="lazy" src="${r.crop}"></a>` : `<a href="${r.shot}" target="_blank">整屏</a>`}</td></tr>`).join('\n')}</table>
<script>const f=()=>{const on=[...document.querySelectorAll('#f input[value]:checked')].map(x=>x.value),fx=document.getElementById('onlyFix').checked;
for(const tr of document.querySelectorAll('#t tr[data-v]'))tr.style.display=on.includes(tr.dataset.v)&&(!fx||tr.dataset.fix==='1')?'':'none'};
document.querySelectorAll('#f input').forEach(x=>x.onchange=f);f();</script></body></html>`;
  fs.writeFileSync(path.join(out, 'report.html'), html);
  console.log(`已写 ${path.relative(REPO, path.join(out, 'report.html'))}: ` + VS.map((v) => `${v} ${rows.filter((r) => r.verdict === v).length}`).join(', '));

  // ======== 刺眼脚本审查(glare.html) ========
  // 不按颜色键的级判, 按元素类型与物理量判(来源键归错不影响), 以参考主题为认可范围:
  //   文字 / 图标 / 空白符: 亮度是正文的几倍(APCA Lc 之比), 彩度(OKLCH C x 100);  线条(细 1px / 粗 >= 2px): 与底色的 ΔE, 比底色多出的彩度;
  //   色块(小 < 2000px² / 大): 与底色的 ΔE, 比底色多出的彩度.
  // 每个量: 不超过参考主题同类实例 P97 为不刺眼; 超过参考主题最大值一成为刺眼; 之间为待看(只有这些给人看). 物理下限: 不比正文亮的字,
  // ΔE < 8 的色块, ΔE < 15 的细线一律不刺眼. 人工标注(glare-labels.json, 在 serve 打开的 /glare.html 上标)优先于脚本判定.
  const KIND = { 图标: 'icon', 活动栏图标: 'icon', 活动栏选中图标: 'icon', 空白符: 'dot', '焦点 / 指示线': 'line', '边框 / 分隔线': 'line', 高亮底: 'block', 色块底: 'block', '徽标 / 按钮底': 'block' };
  const kindOf = (it) => KIND[it.role] || 'text';
  const C = (c) => { const [, a, b] = oklab(rgb(c)); return Math.hypot(a, b) * 100; };
  const bodyLc = Object.fromEntries(themes.map((t) => [t.file, apca(rgb(t.body.fg), rgb(t.body.bg))]));
  const gi = new Map();
  for (const it of items) {
    const kind = kindOf(it);
    if (it.de < 1) continue;
    const cls = kind === 'line' ? ((it.thick || 1) >= 2 ? '粗线' : '细线') : kind === 'block' ? ((it.area || 0) >= 2000 ? '大块' : '小块') : kind === 'icon' ? '图标' : kind === 'dot' ? '空白符' : '文字';
    const k = `${it.theme}|${cls}|${it.fg}|${it.bg}`;
    if (gi.has(k)) { gi.get(k).n += it.count || 1; continue; }
    const m = kind === 'line' || kind === 'block' ? { de: it.de, exC: Math.max(0, C(it.fg) - C(it.bg)) } : { lift: apca(rgb(it.fg), rgb(it.bg)) / bodyLc[it.theme], C: C(it.fg) };
    gi.set(k, { id: k, theme: it.theme, ref: refs.has(it.theme), cls, kind, role: it.role, key: it.key, fg: it.fg, bg: it.bg, m, n: it.count || 1,
      rect: it.rect, thick: it.thick, area: it.area, size: it.size, text: (it.texts || [])[0] || '', crop: it.crop || '', shot: `${SET}/${it.theme}-${it.scene}.jpg` });
  }
  const G = [...gi.values()];
  const qq = (v, p) => { const x = [...v].sort((a, b) => a - b); if (!x.length) return null; const i = (x.length - 1) * p, j = Math.floor(i); return x[j] + (x[Math.min(j + 1, x.length - 1)] - x[j]) * (i - j); };
  const band = {};
  for (const g of G.filter((x) => x.ref)) for (const [mk, v] of Object.entries(g.m)) ((band[g.cls] ||= {})[mk] ||= []).push(v);
  for (const c of Object.keys(band)) for (const mk of Object.keys(band[c])) { const v = band[c][mk]; band[c][mk] = { ok: qq(v, 0.97), max: Math.max(...v), n: v.length }; }
  const MNAME = { lift: '亮度是正文的倍数', C: '彩度', de: '与底色色差 ΔE', exC: '比底色多出的彩度' };
  const fmt = (mk, v) => (mk === 'lift' ? v.toFixed(2) + ' 倍' : v.toFixed(1));
  const glabels = readJson(path.join(out, 'glare-labels.json')) || {};
  for (const g of G) {
    const why = [];
    let state = '不刺眼';
    const floor = (g.kind === 'text' || g.kind === 'icon' || g.kind === 'dot') ? g.m.lift <= 1 : g.kind === 'block' ? g.m.de < 8 : g.cls === '细线' && g.m.de < 15;
    if (!floor) for (const [mk, v] of Object.entries(g.m)) {
      const b = band[g.cls]?.[mk];
      if (!b) continue;
      if (v > b.max * 1.1 + 0.5) { state = '刺眼'; why.push(`${MNAME[mk]} ${fmt(mk, v)}, 超出参考主题最大 ${fmt(mk, b.max)}`); }
      else if (v > b.ok + 0.05) { if (state !== '刺眼') state = '待看'; why.push(`${MNAME[mk]} ${fmt(mk, v)}, 在参考主题 P97 ${fmt(mk, b.ok)} 与最大 ${fmt(mk, b.max)} 之间`); }
    }
    g.auto = state; g.why = why.join('; ');
    g.state = glabels[g.id] ? (glabels[g.id] === '刺眼' ? '刺眼' : '不刺眼') : state;
    g.label = glabels[g.id] || '';
  }
  fs.writeFileSync(path.join(out, 'glare.json'), JSON.stringify({ at, band, groups: G }, null, 1));
  // 看什么: 按类型写明, 并用精确颜色把元素按类型画出来, 旁边是本主题正文
  const LOOK = { text: '文字颜色', icon: '图标颜色', dot: '空白符小点', line: '这条线的颜色', block: '这块底色' };
  const sample = (g) => {
    const t = themes.find((x) => x.file === g.theme);
    const body = `<div class="smp" style="background:${t.body.bg};color:${t.body.fg}">正文 const value = 42;</div>`;
    let el;
    if (g.kind === 'text') el = `<div class="smp" style="background:${g.bg};color:${g.fg};font-size:${Math.max(11, Math.min(g.size || 13, 16))}px">${esc(g.text || 'Aa 示例文字')}</div>`;
    else if (g.kind === 'icon') el = `<div class="smp" style="background:${g.bg};color:${g.fg};font-size:18px">✕ ⚙ ▸ ◉</div>`;
    else if (g.kind === 'dot') el = `<div class="smp" style="background:${g.bg};color:${g.fg}">a·b·c→d</div>`;
    else if (g.kind === 'line') { const w = g.rect.w >= g.rect.h, len = Math.min(360, Math.max(g.rect.w, g.rect.h)), th = g.thick || 1;
      el = `<div class="smp" style="background:${g.bg};height:60px;position:relative"><div style="position:absolute;left:20px;top:${w ? 30 : 6}px;background:${g.fg};width:${w ? len : th}px;height:${w ? th : Math.min(48, len)}px"></div></div>`; }
    else { const sc = Math.min(1, 360 / Math.max(1, g.rect.w), 80 / Math.max(1, g.rect.h));
      el = `<div class="smp" style="background:${g.bg};height:${Math.round(g.rect.h * sc) + 24}px;position:relative"><div style="position:absolute;left:12px;top:12px;background:${g.fg};width:${Math.round(g.rect.w * sc)}px;height:${Math.round(g.rect.h * sc)}px"></div></div>`; }
    return body + el;
  };
  // 没有局部图的从整屏截图(与视口 1:1)按坐标裁出, 叠上虚线框
  // 整屏 jpg 由截图缩到 1600 宽; 视口尺寸取普查记录的 size, 旧普查没有时按状态栏底边估算视口高(宽高比同 jpg 1.6)
  const viewOf = (g) => {
    const r = readJson(path.join(out, SET, 'census', `${g.theme}-${g.shot.slice(-5, -4)}.json`));
    if (r?.size) return r.size;
    const hb = Math.max(...(r?.items || []).filter((i) => /statusbar/.test(i.path)).map((i) => i.rect.y + i.rect.h));
    return isFinite(hb) ? [Math.round(hb * 1.6), hb] : [1600, 1000];
  };
  const shotClip = (g) => {
    const r = g.rect, W = 560, H = 200, [vw, vh] = viewOf(g);
    if (r.x >= vw || r.y >= vh) return `<span class="dim">元素在画面外, 没有截图</span>`;
    const x0 = Math.max(0, Math.min(vw - W, r.x + r.w / 2 - W / 2)), y0 = Math.max(0, Math.min(vh - H, r.y + r.h / 2 - H / 2));
    return `<a href="${g.shot}" target="_blank"><div style="width:${W}px;height:${H}px;position:relative;border:1px solid #ddd;background:url('${g.shot}') -${x0}px -${y0}px / ${vw}px ${vh}px no-repeat">
<div style="position:absolute;left:${r.x - x0 - 3}px;top:${r.y - y0 - 3}px;width:${Math.min(r.w, W) + 6}px;height:${Math.min(r.h, H) + 6}px;outline:2px dashed #FF2BD6"></div></div></a><div class="dim">截图里粉色虚线框住的就是它</div>`;
  };
  const card = (g) => `<div class="card" data-id="${esc(JSON.stringify(g.ids || [g.id]))}" data-state="${g.state}"><div class="hd"><b>${esc(themes.find((x) => x.file === g.theme).label)}</b>${g.ref ? ' <span class="ref">参考主题</span>' : ''} · 看<b class="look">${LOOK[g.kind]}</b>
 <span class="dim">${esc(g.role)}${g.kind === 'line' ? ` · ${g.thick || 1}px x ${Math.max(g.rect.w, g.rect.h)}px` : g.kind === 'block' ? ` · ${g.rect.w}x${g.rect.h}` : ''} · ${esc(g.key || '')}</span></div>
<div class="row"><div class="sm">${sample(g)}<div class="dim">${g.fg} 于 ${g.bg}</div></div><div>${g.crop ? `<a href="${g.crop}" target="_blank"><img loading="lazy" src="${g.crop}"></a><div class="dim">截图里粉色虚线框住的就是它</div>` : shotClip(g)}</div></div>
<div class="why">${esc(g.why)}${g.more ? `<br><span class="dim">同一颜色另有 ${g.more} 处落在别的底色上, 一并标注</span>` : ''}</div><div class="btn"><button data-v="刺眼">刺眼</button><button data-v="还行">还行</button> <span class="lab">${g.label ? '已标: ' + g.label : ''}</span></div></div>`;
  const cnt = (st) => G.filter((g) => g.state === st).length;
  // 同主题同类同色(只是落在不同底色上)合并成一张卡, 一次标注作用于全部; 卡片展示其中最可疑的一处
  const merge = (list) => {
    const m = new Map();
    for (const g of list) { const k = `${g.theme}|${g.cls}|${g.fg}`; (m.get(k) || m.set(k, []).get(k)).push(g); }
    return [...m.values()].map((v) => { v.sort((a, b) => (b.crop ? 1 : 0) - (a.crop ? 1 : 0) || b.why.length - a.why.length); return { ...v[0], ids: v.map((x) => x.id), more: v.length - 1 }; });
  };
  const todo = merge(G.filter((g) => g.auto === '待看' || g.label)).sort((a, b) => (a.label ? 1 : 0) - (b.label ? 1 : 0) || rank(a.theme) - rank(b.theme));
  const bad = merge(G.filter((g) => g.state === '刺眼' && !g.label));
  const ghtml = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>刺眼审查</title><style>
body{font:13px/1.5 -apple-system,sans-serif;margin:16px;color:#222;max-width:1100px}.card{border:1px solid #ccc;border-radius:6px;padding:10px;margin:12px 0}.card[data-done]{opacity:.55}
.hd{margin-bottom:6px}.look{color:#c0c;margin-left:4px}.dim{color:#888;font-size:12px}.ref{background:#e3efff;padding:0 4px;border-radius:3px;font-size:12px}
.row{display:flex;gap:16px;align-items:flex-start}.sm{width:420px}.smp{padding:8px 12px;margin-bottom:4px;font-family:Menlo,monospace;border-radius:4px}
img{max-width:560px;max-height:200px;border:1px solid #ddd}.why{margin:6px 0;color:#555}button{font-size:14px;padding:4px 16px;margin-right:8px}
</style></head><body><h2>刺眼审查</h2><p>脚本已自动判定: 刺眼 ${cnt('刺眼')} 组, 不刺眼 ${cnt('不刺眼')} 组; 下面只列脚本拿不定的 ${G.filter((g) => g.auto === '待看').length} 组(同色合并为 ${todo.filter((g) => !g.label).length} 张卡). 每张卡片左边上一条是本主题正文, 下一条用精确颜色画出要看的那个元素(文字 / 图标 / 线 / 色块), 右边是实际截图. 点 刺眼 或 还行, 结果自动保存, 下次判定以你的标注为准.</p>
<p class="dim">判定口径: 与参考主题同类元素比, 不超过其 P97 为不刺眼, 超出其最大值一成为刺眼, 之间为拿不定. 生成 ${at}</p>
${todo.map(card).join('\n')}
<details><summary>脚本判为刺眼的 ${bad.length} 组(可抽查)</summary>${bad.map(card).join('\n')}</details>
<script>for(const c of document.querySelectorAll('.card'))c.querySelectorAll('button').forEach(b=>b.onclick=async()=>{const r=await fetch('/glare-labels',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({ids:JSON.parse(c.dataset.id),v:b.dataset.v})});
if(r.ok){c.querySelector('.lab').textContent='已标: '+b.dataset.v;c.dataset.done=1}else alert('保存失败: 请用 threshold-lab serve 打开本页')});</script></body></html>`;
  fs.writeFileSync(path.join(out, 'glare.html'), ghtml);
  console.log(`已写 glare.html: 刺眼 ${cnt('刺眼')}, 待看 ${G.filter((g) => g.auto === '待看').length}, 不刺眼 ${cnt('不刺眼')}`);
  process.exit(0);
}

// ======== 服务 ========
const port = Number(rest.includes('--port') ? rest[rest.indexOf('--port') + 1] : 9340);
const MIME = { '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json', '.html': 'text/html; charset=utf-8' };
const readBody = (req) => new Promise((res) => { let b = ''; req.on('data', (d) => { b += d; }); req.on('end', () => res(JSON.parse(b))); });
http.createServer(async (req, res) => {
  const url = decodeURIComponent(req.url.split('?')[0]);
  const json = (o) => { res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify(o)); };
  if (url === '/') { res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); return res.end(PAGE); }
  if (url === '/keys') { res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); return res.end(KEYS_PAGE); }
  if (url === '/data.json') return json(data());
  if (url === '/keys.json') {
    return json(keysData({
      registry: readJson(path.join(REPO, 'assets/vscode/color-registry.json')).colors,
      originals: Object.fromEntries(allThemes.map((t) => [t.file, readJson(path.join(REPO, 'assets/source', `${t.file}.json`))])),
      fulls: Object.fromEntries(allThemes.map((t) => [t.file, themeJson(t.file)])),
      saved: readJson(path.join(out, 'key-levels.json')),
      effective: Object.fromEntries(allThemes.map((t) => [t.file, readJson(path.join(out, SET, 'census', `${t.file}-vars.json`))])),
      defaults: readJson(path.join(out, 'analysis', 'vscode-defaults.json')) || {},
      docs: readJson(path.join(REPO, 'assets/vscode/color-docs.json'))?.colors || {},
    }));
  }
  if (req.method === 'POST' && url === '/glare-labels') {
    const j = await readBody(req), f = path.join(out, 'glare-labels.json'), labels = readJson(f) || {};
    for (const id of j.ids || [j.id]) labels[id] = j.v;
    fs.writeFileSync(f, JSON.stringify(labels, null, 1));
    return json({ ok: true });
  }
  if (req.method === 'POST' && (url === '/submit' || url === '/keys-submit')) {
    const j = await readBody(req);
    const at = stamp('+%Y-%m-%d %H:%M:%S'), ts = stamp('+%Y%m%d_%H%M%S');
    if (url === '/keys-submit') {
      const doc = JSON.stringify({ at, overrides: j.overrides, levels: j.levels }, null, 1);
      fs.writeFileSync(path.join(out, 'key-levels.json'), doc);
      fs.writeFileSync(path.join(out, `key-levels-${ts}.json`), doc);
      console.log(`收到键分层复核 ${at}: 改动 ${Object.keys(j.overrides).length} 个`);
    } else {
      const { labels, ...conf } = j;
      const doc = JSON.stringify({ at, ...conf }, null, 1);
      fs.writeFileSync(path.join(out, 'thresholds.json'), doc);
      fs.writeFileSync(path.join(out, `thresholds-${ts}.json`), doc);
      fs.writeFileSync(path.join(out, 'labels.json'), JSON.stringify(labels, null, 1));
      console.log(`收到门槛提交 ${at}: ${Object.keys(labels).length} 条标注`);
    }
    return json({ ok: true, at });
  }
  const f = path.resolve(out, '.' + url);
  if (!f.startsWith(out) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.statusCode = 404; return res.end(); }
  res.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(port, '127.0.0.1', () => console.log(`门槛标定台: http://127.0.0.1:${port}/`));

const PAGE = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>门槛标定台</title>
<style>
body{margin:0;font:13px/1.5 -apple-system,"PingFang SC",sans-serif;background:#1b1d22;color:#ddd}
header{position:sticky;top:0;z-index:10;background:#24272e;padding:8px 14px;border-bottom:1px solid #3a3e48;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center}
header b{color:#fff} select,input[type=number]{background:#30343c;color:#ddd;border:1px solid #4a4f5a;border-radius:4px;padding:1px 4px} input[type=number]{width:58px}
button{background:#30343c;color:#ddd;border:1px solid #4a4f5a;border-radius:4px;padding:2px 10px;cursor:pointer} button.pri{background:#3d6fb6;color:#fff;border-color:#3d6fb6}
a{color:#7ab} .dim{color:#8a93a0} .wrap{display:grid;grid-template-columns:190px 1fr;min-height:calc(100vh - 46px)}
nav{border-right:1px solid #3a3e48;padding:8px 0} nav div{padding:3px 12px;cursor:pointer;display:flex;justify-content:space-between} nav div.on{background:#2f4a6e;color:#fff} nav div:hover{background:#2a2e36}
nav .sep{border-top:1px solid #3a3e48;margin:6px 0;padding:0;cursor:default} nav .gt{color:#9aa;font-size:11px;cursor:default;padding-top:6px}
main{padding:10px 16px} h2{margin:4px 0 8px;color:#fff;font-size:17px} h3{margin:16px 0 6px;color:#fff;font-size:14px}
table{border-collapse:collapse;font-size:12px;margin:6px 0} td,th{padding:3px 8px;border-bottom:1px solid #30343c;text-align:right} th:first-child,td:first-child{text-align:left}
.bandbar{display:flex;height:10px;border-radius:3px;overflow:hidden;margin:4px 0;max-width:920px} .z0{background:#c0392b}.z1{background:#3b8f5a}.z2{background:#9a3aa0}
.chips span{display:inline-block;padding:1px 8px;margin:2px;border:1px solid #4a4f5a;border-radius:10px;cursor:pointer;font-size:12px} .chips span.on{background:#3d6fb6;color:#fff;border-color:#3d6fb6}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.card{background:#24272e;border:1px solid #353944;border-radius:6px;padding:6px;font-size:12px}
.card.l-low{border-color:#c0392b}.card.l-ok{border-color:#3b8f5a}.card.l-high{border-color:#9a3aa0}
.card img{max-width:100%;max-height:120px;display:block;margin-bottom:4px;cursor:zoom-in}
.syn{padding:6px 8px;border-radius:3px;margin-bottom:4px;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sw{display:inline-block;width:14px;height:14px;border:1px solid #888;vertical-align:-3px;position:relative;cursor:pointer;margin:0 2px}
.sw:hover::after{content:attr(data-hex);position:absolute;z-index:20;left:20px;top:-46px;width:110px;height:110px;background:inherit;border:2px solid #fff;
 box-shadow:0 4px 16px #000a;color:#fff;font:12px monospace;display:flex;align-items:flex-end;padding:3px;box-sizing:border-box;text-shadow:0 0 3px #000,0 0 3px #000}
.lb button{padding:0 6px;font-size:11px;margin:3px 3px 0 0} .lb button.on.low{background:#c0392b;color:#fff} .lb button.on.ok{background:#3b8f5a;color:#fff} .lb button.on.high{background:#9a3aa0;color:#fff}
.goal{color:#9cc3ff} .bad{color:#f07070} .good{color:#6c6} code{color:#e6c07b}
svg text{fill:#9aa;font-size:10px}
.mx{display:grid;grid-template-columns:70px repeat(3,1fr);gap:6px;max-width:1100px} .mx .h{color:#9aa;font-size:12px;align-self:center}
.mx .c{background:#24272e;border:1px solid #353944;border-radius:6px;padding:4px;min-height:60px;font-size:11px} .mx .c img{max-width:100%;max-height:70px;display:block}
#zoom{position:fixed;inset:0;background:#000d;display:none;z-index:50;align-items:center;justify-content:center} #zoom img{max-width:96vw;max-height:94vh}
</style></head><body>
<header><b>门槛标定台</b><a href="/keys">颜色键分层复核</a><span class="dim" id="prog"></span>
<label title="原主题取值与底色 ΔE < 1 的线条与层次底, 即原设计不画线 / 不分层; 焦点框, 选区, 当前匹配不排除"><input type="checkbox" id="exSame"> 排除同色线条与层次底</label>
<label>主题 <select id="fTheme"><option value="">全部</option><option value="dark">只看深色</option><option value="light">只看浅色</option><option value="ref">只看参考主题</option><option value="other">只看其他主题</option></select></label>
<label title="参考主题: 用户认可的原主题; 按参考主题推荐时, 目标与下限只用参考主题的数据, 绝对下限保证参考主题被拦下不超过约 5%">推荐依据 <select id="recBase"><option value="ref">参考主题</option><option value="all">全部主题</option></select></label>
<button id="reload">刷新数据</button><button class="pri" id="submit">提交门槛与标注</button><span id="msg" class="dim"></span></header>
<div class="wrap"><nav id="nav"></nav><main id="main">加载中…</main></div><div id="zoom"><img></div>
<script>
const GROUPS = { 内容: '必须读得清的字与图标', 暗化: '刻意压低, 要认得出', 线条: '边框, 分隔线, 焦点框, 指示线', 底色: '强调底, 状态底, 层次底' };
const LV = ['强', '中', '弱'];
const LEVELS = Object.keys(GROUPS).flatMap((g) => LV.map((l) => g + l));
const LADDERS = [['内容强', '内容中', '内容弱', '暗化强', '暗化中', '暗化弱'], ['线条强', '线条中', '线条弱'], ['底色强', '底色中', '底色弱']];
const nb = (k, d) => { const L = LADDERS.find((x) => x.includes(k)); return L[L.indexOf(k) + d] || null; };
// 规范锚点(相对正文 %): 前景按 Material / Apple 的透明度梯度, 底色按 Material 状态叠层(悬停 8%, 聚焦 / 选中 10~16%)
const ANCHOR = { 内容强: 100, 内容中: 87, 内容弱: 60, 暗化强: 45, 暗化中: 30, 暗化弱: 18, 线条强: 50, 线条中: 35, 线条弱: 15, 底色强: 55, 底色中: 12, 底色弱: 8 };
// 绝对下限(规范值): 前景 APCA Lc(一般内容 60, 大字 / 图标 45, 任何文字最低 30); 暗化弱, 线条, 底色 OKLab ΔE x 100(刚可辨约 2, 焦点 3:1 约合 20)
const ABS0 = { 内容强: 50, 内容中: 45, 内容弱: 35, 暗化强: 30, 暗化中: 20, 暗化弱: 3, 线条强: 20, 线条中: 10, 线条弱: 3, 底色强: 15, 底色中: 5, 底色弱: 2 };
// 参考主题: 用户认可的原主题(不做调整时就喜欢的), 推荐值以它们为准: 门槛要让它们基本合格, 主要拦其余主题里真正有问题的地方
const REF0 = ['one-dark', 'one-light', 'ayu-dark', 'ayu-light', 'moka-dark', 'moka-light', 'github-light', 'sunlit-light'];
const isRef = (t) => (st.ref || REF0).includes(t);
const tmean = (v) => { const s = [...v].sort((a, b) => a - b), c = Math.floor(s.length * 0.2), t = s.length > 4 ? s.slice(c, s.length - c) : s; return mean(t); };
// 暗化弱(空白符等)的 Lc 多在 APCA 截零区间, 和线条, 底色一样用 ΔE
const ABS = (k) => (/^(内容|暗化强|暗化中)/.test(k) ? 'Lc' : 'ΔE');
const absOf = (it) => (ABS(lvOf(it)) === 'Lc' ? it.apca : it.de);
// 相对约束: a 的相对指标中位数 / b 的 要落在 [min, max]; a, b 是普查角色
const RULES0 = [
  { a: '非活动标签', b: '活动标签', min: 0.6, max: 0.9, why: '分得出当前标签, 其余标签仍能读' },
  { a: '注释', b: '代码', min: 0.4, max: 0.85, why: '注释比代码弱, 但不至于读不出' },
  { a: '次要文字', b: '主要文字', min: 0.6, max: 0.95, why: '列表里描述弱于主标签' },
  { a: '行号', b: '当前行号', min: 0.4, max: 0.85, why: '当前行号比其他行号醒目' },
  { a: '活动栏图标', b: '活动栏选中图标', min: 0.5, max: 0.9, why: '分得出当前视图' },
];
const LBL = [['low', '不及目标'], ['ok', '合适'], ['high', '超出目标']];
const LS = 'threshold-lab-v4';
let D, REC, st = JSON.parse(localStorage.getItem(LS) || '{}');
st.labels ||= {}; st.over ||= {}; st.lv ||= {}; st.sep ||= {}; st.page ||= 'overview'; st.view ||= 'edge'; st.roleF ||= {};
const save = () => localStorage.setItem(LS, JSON.stringify(st));
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sw = (h) => '<span class="sw" style="background:' + h + '" data-hex="' + h + '"></span>';
const lvOf = (it) => st.over[it.id] || it.level;
const med = (v) => { if (!v.length) return NaN; const s = [...v].sort((a, b) => a - b); const n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
const mean = (v) => v.reduce((a, b) => a + b, 0) / v.length;
const q = (v, p) => { const s = [...v].sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.max(0, Math.round(p * (s.length - 1))))]; };
const trim = (v) => { const s = [...v].sort((a, b) => a - b); return s.length > 6 ? s.slice(2, -2) : s; };
const comp = (v) => { const t = trim(v); return t.length ? (med(t) + mean(t)) / 2 : NaN; };
const r1 = (x) => Math.round(x * 10) / 10;
// 主题 x 级 x 色对 去重(跨场景)
function pairs() {
  const f = document.getElementById('fTheme').value;
  const th = Object.fromEntries(D.themes.map((t) => [t.file, t]));
  const seen = new Map();
  for (const it of D.items) {
    if (st.exSame !== false && it.de < 1 && (/^线条/.test(lvOf(it)) || lvOf(it) === '底色弱') && !/focus|selection|findMatch|Cursor/i.test(it.key || '')) continue;
    if (f === 'dark' && !th[it.theme].dark) continue;
    if (f === 'light' && th[it.theme].dark) continue;
    if (f === 'ref' && !isRef(it.theme)) continue;
    if (f === 'other' && isRef(it.theme)) continue;
    const k = it.theme + '|' + it.role + '|' + it.fg + '|' + it.bg;
    const g = seen.get(k);
    if (!g) seen.set(k, { ...it, n: it.count });
    else { g.n += it.count; if (!g.crop && it.crop) Object.assign(g, { crop: it.crop, scene: it.scene, id: it.id, path: it.path, texts: it.texts }); }
  }
  return [...seen.values()];
}
// 每个主题每级的中位数
function cells(P) {
  const m = {};
  for (const t of D.themes) for (const k of LEVELS) { const v = P.filter((x) => x.theme === t.file && lvOf(x) === k).map((x) => x.rd); if (v.length) (m[t.file] ||= {})[k] = med(v); }
  return m;
}
// 推荐值: 目标 = 各主题中位数掐头去尾的折中; 上下限 = 实例 P10 / P90; 绝对下限 = 实例绝对指标 P10; 区分度 = 各主题差值掐头去尾后的 P25, 不低于 SEP_FLOOR
const SEP_FLOOR = 5;
const sepRec = (d) => (d.length ? { min: r1(Math.max(SEP_FLOOR, q(trim(d), 0.25))), med: r1(med(trim(d))) } : null);
function recommend() {
  const P = pairs(), M = cells(P), R = { lv: {}, inGroup: {}, cross: {} };
  const base = (st.recBase || 'ref') === 'ref' ? D.themes.filter((t) => isRef(t.file)) : D.themes;
  for (const k of LEVELS) {
    const inst = P.filter((x) => lvOf(x) === k), bi = inst.filter((x) => base.some((t) => t.file === x.theme));
    const per = base.map((t) => bi.filter((x) => x.theme === t.file).map((x) => x.rd)).filter((v) => v.length);
    const pct = per.length ? r1(tmean(per.map(med))) : ANCHOR[k];
    // 绝对下限: 规范值, 但不高于依据主题实例的 P5(依据主题被拦下不超过约 5%)
    const absP5 = bi.length ? Math.floor(q(bi.map(absOf), 0.05)) : ABS0[k];
    // 修复下限: 依据主题实例合在一起的 P5(好主题几乎都在线上, 线下的是它们里也确实偏弱的); 各主题 P10 的中位数默认会拦下每套约一成, 已弃用
    R.lv[k] = { pct, lo: bi.length ? r1(q(bi.map((x) => x.rd), 0.05)) : r1(ANCHOR[k] * 0.6), p90: per.length ? r1(med(per.map((v) => q(v, 0.9)))) : null,
      abs: Math.min(ABS0[k], absP5), absSpec: ABS0[k], anchor: ANCHOR[k], n: inst.length, themes: per.length };
  }
  // 上限 = 与强一档目标的中点; 梯子顶端用典型上沿. 修复下限不高于混档线(无弱一档时不高于目标): 每主题样本少时 P10 就是样本本身, 会把下限抬到目标
  for (const k of LEVELS) {
    const up = nb(k, -1), dn = nb(k, 1), r = R.lv[k];
    r.hi = up ? r1((r.pct + R.lv[up].pct) / 2) : r.p90 ?? r1(r.pct * 1.3);
    r.lo = Math.min(r.lo, dn ? r1((r.pct + R.lv[dn].pct) / 2) : r.pct);
  }
  for (const g of Object.keys(GROUPS)) for (const [a, b] of [['强', '中'], ['中', '弱']]) {
    const d = base.map((t) => (M[t.file]?.[g + a] ?? NaN) - (M[t.file]?.[g + b] ?? NaN)).filter((x) => !isNaN(x));
    R.inGroup[g + a + '>' + b] = sepRec(d);
  }
  const gs = Object.keys(GROUPS);
  for (const l of LV) for (let i = 0; i < gs.length; i++) for (let j = i + 1; j < gs.length; j++) {
    const d = base.map((t) => Math.abs((M[t.file]?.[gs[i] + l] ?? NaN) - (M[t.file]?.[gs[j] + l] ?? NaN))).filter((x) => !isNaN(x));
    R.cross[gs[i] + l + '|' + gs[j] + l] = sepRec(d);
  }
  return R;
}
const lvCfg = (k) => ({ ...(D.saved?.levels?.[k] || REC.lv[k]), ...(st.lv[k] || {}) });
// 混档线: 本级目标与弱一档目标的中点, 跟随页面上改过的目标
const mixLo = (k) => { const dn = nb(k, 1); return dn ? r1((lvCfg(k).pct + lvCfg(dn).pct) / 2) : null; };
const sepCfg = (k, kind) => st.sep[k] ?? D.saved?.sep?.[kind]?.[k] ?? REC[kind][k]?.min ?? null;
// 分区: 0 不及目标(低于修复下限或绝对下限), 3 偏淡(低于混档线, 像弱一档; 只给排查), 1 合适, 2 超出目标(高于上限, 像强一档)
const disabled = (it) => it.role === '禁用' || /disabled/i.test(it.key || '');
const zone = (it) => { const k = lvOf(it), c = lvCfg(k), m = mixLo(k), low = it.rd < c.lo || absOf(it) < (c.abs || 0); return low ? (disabled(it) ? 3 : 0) : m != null && it.rd < m ? 3 : it.rd > c.hi ? 2 : 1; };
const ZC = ['#e05050', '#4caf6a', '#c060c0', '#e0a030'];
const zcount = (L) => { const z = [0, 0, 0, 0]; L.forEach((x) => z[zone(x)]++); return z; };
const zhtml = (z) => '<span class="bad">' + z[0] + '</span> / <span style="color:#e0a030">' + z[3] + '</span> / <span class="good">' + z[1] + '</span> / <span style="color:#c8c">' + z[2] + '</span>';
function nav() {
  const P = pairs(), cnt = {};
  P.forEach((it) => { cnt[lvOf(it)] = (cnt[lvOf(it)] || 0) + 1; });
  let h = '<div data-p="overview" class="' + (st.page === 'overview' ? 'on' : '') + '"><span>各级总览</span></div>';
  for (const g of Object.keys(GROUPS)) {
    h += '<div class="gt">' + g + '组</div>';
    for (const l of LV) { const k = g + l; h += '<div data-p="lv:' + k + '" class="' + (st.page === 'lv:' + k ? 'on' : '') + '"><span>' + k + '</span><span class="dim">' + (cnt[k] || 0) + '</span></div>'; }
  }
  h += '<div class="sep"></div>' + [['sep', '区分度'], ['matrix', '分级矩阵(看效果)'], ['rules', '相对约束'], ['labeled', '已标注 ' + Object.keys(st.labels).length]]
    .map(([k, t]) => '<div data-p="' + k + '" class="' + (st.page === k ? 'on' : '') + '"><span>' + t + '</span></div>').join('');
  document.getElementById('nav').innerHTML = h;
}
function card(it) {
  const k = lvOf(it), c = lvCfg(k), l = st.labels[it.id];
  const prev = it.crop ? '<img loading="lazy" src="' + it.crop + '">' : '<div class="syn" style="background:' + it.bg + ';color:' + it.fg + '">' + esc((it.texts || [])[0] || 'Aa 示例 Sample 123') + '</div>';
  return '<div class="card' + (l ? ' l-' + l : '') + '" data-id="' + esc(it.id) + '">' + prev +
    '<b>' + esc(it.theme) + '</b> ' + it.scene + ' · ' + esc(it.role) + ' · <code>' + esc(it.key || '-') + '</code>' + (it.keyNote ? ' <span class="bad">(' + it.keyNote + ', 按角色归级)</span>' : '') + (st.over[it.id] ? ' <span class="goal">(单独改级)</span>' : '') +
    '<br><span class="goal">' + k + ': 目标 ' + c.pct + '% (' + c.lo + '~' + c.hi + '%)</span>' +
    '<br>相对 <b class="' + (zone(it) === 1 ? 'good' : 'bad') + '">' + it.rd + '%</b> · ' + ABS(k) + ' ' + absOf(it) + ' · Lc ' + it.apca + ' · ΔE ' + it.de + ' · WCAG ' + it.wcag +
    '<br>' + sw(it.fg) + it.fg + ' 于 ' + sw(it.bg) + it.bg + (it.n > 1 ? ' · ' + it.n + ' 处' : '') +
    '<br><span class="dim">' + esc(it.path || '') + (it.texts?.length ? ' · ' + esc(it.texts.join(' / ')) : '') + '</span>' +
    '<div class="lb">' + LBL.map(([x, n]) => '<button data-l="' + x + '" class="' + x + (l === x ? ' on' : '') + '">' + n + '</button>').join('') +
    ' 改级 <select data-over="1"><option value="">按键</option>' + LEVELS.map((x) => '<option' + (st.over[it.id] === x ? ' selected' : '') + '>' + x + '</option>').join('') + '</select></div></div>';
}
function suggest(list) {
  const v = (k) => list.filter((x) => st.labels[x.id] === k).map((x) => x.rd);
  const low = v('low'), ok = v('ok'), high = v('high'), s = {};
  if (low.length && ok.length) { const a = Math.max(...low), b = Math.min(...ok); s.lo = a < b ? r1((a + b) / 2) : null; s.loNote = a < b ? '' : '标注有交叉(不及最高 ' + a + ', 合适最低 ' + b + ')'; }
  if (high.length && ok.length) { const a = Math.min(...high), b = Math.max(...ok); s.hi = a > b ? r1((a + b) / 2) : null; s.hiNote = a > b ? '' : '标注有交叉(超出最低 ' + a + ', 合适最高 ' + b + ')'; }
  return s;
}
function overview() {
  const P = pairs();
  let h = '<h2>各级总览</h2><p class="dim">相对 = 明度差 / 本主题正文明度差 x 100%; 绝对: 内容与暗化强 / 中用 APCA Lc, 暗化弱, 线条与底色用 OKLab ΔE x 100. 归级按元素自身颜色的来源键(颜色键分层' +
    (D.keyLevelsAt ? '复核于 ' + D.keyLevelsAt : '尚未复核, 用自动归类') + '). 推荐规则 v2: 目标 = 各主题中位数的 20% 截尾均值(锚点只作检验); 下限 = 各主题 P10 的中位数(步骤与门禁用); 混档线 = 与弱一档目标的中点(排查用);' +
    ' 上限 = 与强一档目标的中点; 绝对下限 = 规范值. 黄色 = 实测目标与锚点差超过 15, 或绝对下限挡下超过 15% 的原主题实例.</p>';
  h += '<table><tr><th>级</th><th>实例</th><th>主题</th><th>目标 %</th><th>锚点</th><th>下限 %</th><th>混档线</th><th>上限 %</th><th>绝对下限</th><th>挡下 参考 / 其他</th><th>推荐(目标 / 下 / 上)</th><th>不及 / 偏淡 / 合适 / 超出</th><th>不及 参考 / 其他</th><th>提示</th></tr>';
  for (const k of LEVELS) {
    const c = lvCfg(k), R = REC.lv[k], L = P.filter((x) => lvOf(x) === k), z = zcount(L);
    const pc = (A, f) => (A.length ? Math.round((A.filter(f).length / A.length) * 100) : 0);
    const Lr = L.filter((x) => isRef(x.theme)), Lo = L.filter((x) => !isRef(x.theme));
    const blocked = pc(Lr, (x) => absOf(x) < (c.abs || 0)), blockedO = pc(Lo, (x) => absOf(x) < (c.abs || 0));
    const lowR = pc(Lr, (x) => zone(x) === 0), lowO = pc(Lo, (x) => zone(x) === 0);
    const inp = (f) => '<td><input type="number" step="0.5" data-lv="' + k + '" data-f="' + f + '" value="' + (c[f] ?? 0) + '">' + (f === 'abs' ? ' ' + ABS(k) : '') + '</td>';
    h += '<tr><td><a href="#" data-go="lv:' + k + '">' + k + '</a></td><td>' + L.length + '</td><td>' + R.themes + '</td>' + inp('pct') +
      '<td style="color:' + (Math.abs(c.pct - R.anchor) > 15 ? '#e0a030' : '#8a93a0') + '">' + R.anchor + '</td>' + inp('lo') + '<td class="dim">' + (mixLo(k) ?? '-') + '</td>' + inp('hi') + inp('abs') +
      '<td style="color:' + (blocked > 5 ? '#e0a030' : '#8a93a0') + '">' + blocked + '% / ' + blockedO + '%</td><td class="dim">' + R.pct + ' / ' + R.lo + ' / ' + R.hi + '</td><td>' + zhtml(z) + '</td><td style="color:' + (lowR > 10 ? '#e0a030' : '#8a93a0') + '">' + lowR + '% / ' + lowO + '%</td><td style="color:#e0a030;text-align:left">' + [
        nb(k, 1) && c.pct <= lvCfg(nb(k, 1)).pct ? '目标不高于弱一档(' + nb(k, 1) + ' ' + lvCfg(nb(k, 1)).pct + '), 档位倒挂' : '',
        Math.abs(c.pct - R.anchor) > 15 ? '与锚点差 ' + r1(c.pct - R.anchor) : '', blocked > 5 ? '参考主题被绝对下限挡下 ' + blocked + '%' : '', lowR > 10 ? '参考主题不及目标 ' + lowR + '%' : ''].filter(Boolean).join('; ') + '</td></tr>';
  }
  h += '</table><button id="resetLv">全部恢复推荐值</button>';
  h += '<h3>参考主题 <span class="dim" style="font-size:12px">用户认可的原主题; 推荐依据选"参考主题"时, 目标与下限只用它们的数据, 绝对下限保证它们被拦下不超过约 5%</span></h3><div class="chips">' +
    D.themes.map((t) => '<span data-ref="' + t.file + '" class="' + (isRef(t.file) ? 'on' : '') + '">' + esc(t.label) + '</span>').join('') + '</div>';
  h += '<h3>各主题正文基准</h3><table><tr><th>主题</th><th>正文</th><th>Lc</th><th>明度差</th></tr>' + D.themes.map((t) =>
    '<tr><td>' + esc(t.label) + '</td><td>' + sw(t.body.fg) + t.body.fg + ' 于 ' + sw(t.body.bg) + t.body.bg + '</td><td>' + t.body.lc + '</td><td>' + t.body.dl + '</td></tr>').join('') + '</table>';
  return h;
}
// 组合图: 上半是相对指标直方图(点柱子看该区间实例), 下半是 相对指标(横) x 绝对指标(纵) 散点(点圆点看该实例);
// 竖线 下限 / 目标 / 上限, 横线 绝对下限, 都可拖动; 红区 = 不及目标(在下限左边, 或在绝对下限下面), 紫区 = 超出目标
function plot(k, c, P) {
  const X0 = 46, W = 880, HH = 110, Y1 = 150, HS = 230, MAX = /^底色/.test(k) ? 60 : 160, bins = 64;
  const absV = P.map(absOf), YMAX = Math.max(10, (c.abs || 0) * 1.4, q(absV.length ? absV : [10], 0.97) * 1.15);
  const xo = (v) => X0 + (Math.min(MAX, Math.max(0, v)) / MAX) * W, yo = (a) => Y1 + HS - (Math.min(YMAX, Math.max(0, a)) / YMAX) * HS;
  const hist = new Array(bins).fill(0);
  P.forEach((x) => hist[Math.min(bins - 1, Math.floor((Math.min(MAX, Math.max(0, x.rd)) / MAX) * bins))]++);
  const mx = Math.max(1, ...hist);
  let g = '<svg id="plot" data-k="' + k + '" data-x0="' + X0 + '" data-w="' + W + '" data-max="' + MAX + '" data-y1="' + Y1 + '" data-hs="' + HS + '" data-ymax="' + YMAX + '" width="' + (X0 + W + 120) + '" height="' + (Y1 + HS + 30) + '" style="user-select:none">';
  const ml = mixLo(k);
  hist.forEach((n, i) => { const v = ((i + 0.5) / bins) * MAX; const col = v < c.lo ? '#c0392b' : ml != null && v < ml ? '#b07a20' : v > c.hi ? '#9a3aa0' : '#3b8f5a';
    g += '<rect data-bin="' + i + '" x="' + (X0 + (i * W) / bins) + '" y="' + (10 + HH - (n / mx) * HH) + '" width="' + (W / bins - 1) + '" height="' + Math.max(1, (n / mx) * HH) + '" fill="' + col + '" opacity="' + (st.bin === i ? 1 : 0.75) + '" style="cursor:pointer"><title>' + n + ' 个</title></rect>'; });
  g += '<text x="2" y="20">实例数</text><text x="2" y="' + (Y1 + 10) + '">' + ABS(k) + '</text><text x="' + (X0 + W - 60) + '" y="' + (Y1 + HS + 26) + '">相对 %</text>';
  // 散点区底色分区
  g += '<rect data-g="zlo" x="' + X0 + '" y="' + Y1 + '" width="' + (xo(c.lo) - X0) + '" height="' + HS + '" fill="#c0392b" opacity="0.12"/>';
  g += '<rect data-g="zabs" x="' + X0 + '" y="' + yo(c.abs || 0) + '" width="' + W + '" height="' + (Y1 + HS - yo(c.abs || 0)) + '" fill="#c0392b" opacity="0.12"/>';
  g += '<rect data-g="zhi" x="' + xo(c.hi) + '" y="' + Y1 + '" width="' + (X0 + W - xo(c.hi)) + '" height="' + HS + '" fill="#9a3aa0" opacity="0.12"/>';
  g += '<rect x="' + X0 + '" y="' + Y1 + '" width="' + W + '" height="' + HS + '" fill="none" stroke="#3a3e48"/>';
  for (let v = 0; v <= MAX; v += MAX > 100 ? 20 : 10) g += '<text x="' + (xo(v) - 6) + '" y="' + (Y1 + HS + 14) + '">' + v + '</text><line x1="' + xo(v) + '" x2="' + xo(v) + '" y1="' + Y1 + '" y2="' + (Y1 + HS) + '" stroke="#2c3038"/>';
  const ystep = YMAX > 60 ? 20 : YMAX > 25 ? 10 : 5;
  for (let a = 0; a <= YMAX; a += ystep) g += '<text x="' + (X0 - 26) + '" y="' + (yo(a) + 3) + '">' + a + '</text>';
  // 散点: 标注过的描边
  P.forEach((x) => { const l = st.labels[x.id]; const z = zone(x);
    g += '<circle data-pt="' + esc(x.id) + '" cx="' + xo(x.rd) + '" cy="' + yo(absOf(x)) + '" r="' + (st.pick === x.id ? 6 : l ? 4.5 : 3) + '" fill="' + (isRef(x.theme) ? ZC[z] : 'none') + '" fill-opacity="0.75" stroke="' + (l ? { low: '#ff9a9a', ok: '#b8ffb8', high: '#ffb8ff' }[l] : st.pick === x.id ? '#fff' : isRef(x.theme) ? 'none' : ZC[z]) + '" stroke-width="' + (isRef(x.theme) ? 2 : 1.4) + '" style="cursor:pointer"><title>' + esc(x.theme + ' ' + x.role + ' ' + (x.key || '') + ' 相对 ' + x.rd + '% ' + ABS(k) + ' ' + absOf(x)) + '</title></circle>'; });
  // 可拖动的分界线
  const vline = (f, v, col, name, dash) => '<g data-g="' + f + '"><line x1="' + xo(v) + '" x2="' + xo(v) + '" y1="4" y2="' + (Y1 + HS) + '" stroke="' + col + '" stroke-width="1.5"' + (dash ? ' stroke-dasharray="4 3"' : '') + '/>' +
    '<line data-drag="' + f + '" x1="' + xo(v) + '" x2="' + xo(v) + '" y1="4" y2="' + (Y1 + HS) + '" stroke="transparent" stroke-width="12" style="cursor:ew-resize"/>' +
    '<circle data-drag="' + f + '" cx="' + xo(v) + '" cy="' + (Y1 - 12) + '" r="6" fill="' + col + '" style="cursor:ew-resize"/><text data-t="1" x="' + (xo(v) + 8) + '" y="' + (Y1 - 22) + '" style="fill:' + col + ';font-size:11px">' + name + ' ' + v + '%</text></g>';
  if (ml != null) g += '<rect x="' + xo(c.lo) + '" y="' + Y1 + '" width="' + Math.max(0, xo(ml) - xo(c.lo)) + '" height="' + HS + '" fill="#e0a030" opacity="0.08"/>' +
    '<line x1="' + xo(ml) + '" x2="' + xo(ml) + '" y1="' + (Y1 - 4) + '" y2="' + (Y1 + HS) + '" stroke="#e0a030" stroke-width="1.2" stroke-dasharray="2 3"/><text x="' + (xo(ml) + 4) + '" y="' + (Y1 + 12) + '" style="fill:#e0a030;font-size:11px">混档线 ' + ml + '%</text>';
  g += vline('lo', c.lo, '#ff7b7b', '下限', false) + vline('pct', c.pct, '#9cc3ff', '目标', true) + vline('hi', c.hi, '#d58ad5', '上限', false);
  const ya = yo(c.abs || 0);
  g += '<g data-g="abs"><line x1="' + X0 + '" x2="' + (X0 + W) + '" y1="' + ya + '" y2="' + ya + '" stroke="#ffb347" stroke-width="1.5"/>' +
    '<line data-drag="abs" x1="' + X0 + '" x2="' + (X0 + W) + '" y1="' + ya + '" y2="' + ya + '" stroke="transparent" stroke-width="12" style="cursor:ns-resize"/>' +
    '<circle data-drag="abs" cx="' + (X0 + W + 10) + '" cy="' + ya + '" r="6" fill="#ffb347" style="cursor:ns-resize"/><text data-t="1" x="' + (X0 + W + 20) + '" y="' + (ya + 4) + '" style="fill:#ffb347;font-size:11px">绝对下限 ' + (c.abs || 0) + ' ' + ABS(k) + '</text></g>';
  return g + '</svg>';
}
function lvPage(k) {
  const c = lvCfg(k), all = pairs().filter((x) => lvOf(x) === k);
  const roles = [...new Set(all.map((x) => x.role))], rf = st.roleF[k] || [];
  const P = rf.length ? all.filter((x) => rf.includes(x.role)) : all;
  const svg = plot(k, c, P);
  const z = zcount(P);
  const tot = P.length || 1, sg = suggest(all);
  const keys = {}; all.forEach((x) => { keys[x.key || '-'] = (keys[x.key || '-'] || 0) + 1; });
  let h = '<h2>' + k + ' <span class="dim" style="font-size:12px">' + GROUPS[k.slice(0, 2)] + ' · ' + P.length + ' 组色对</span></h2>';
  h += '<div class="chips">角色: ' + roles.map((r) => '<span data-rf="' + esc(r) + '" class="' + (rf.includes(r) ? 'on' : '') + '">' + esc(r) + ' ' + all.filter((x) => x.role === r).length + '</span>').join('') + ' <span class="dim">(不选为全部)</span></div>';
  h += svg + '<div class="bandbar"><div class="z0" style="width:' + (z[0] / tot) * 100 + '%"></div><div style="background:#b07a20;width:' + (z[3] / tot) * 100 + '%"></div><div class="z1" style="width:' + (z[1] / tot) * 100 + '%"></div><div class="z2" style="width:' + (z[2] / tot) * 100 + '%"></div></div>';
  h += '<div>不及目标 <b class="bad">' + z[0] + '</b> · 偏淡(像弱一档) <b style="color:#e0a030">' + z[3] + '</b> · 合适 <b class="good">' + z[1] + '</b> · 超出目标 <b style="color:#c8c">' + z[2] + '</b> · ' +
    ['pct', 'lo', 'hi', 'abs'].map((f) => ({ pct: '目标', lo: '下限', hi: '上限', abs: '绝对下限 ' + ABS(k) })[f] + ' <input type="number" step="0.5" data-lv="' + k + '" data-f="' + f + '" value="' + (c[f] ?? 0) + '">').join(' ') +
    ' <span class="dim">按标注建议: 下限 ' + (sg.lo ?? '-') + (sg.loNote ? ' ' + sg.loNote : '') + ', 上限 ' + (sg.hi ?? '-') + (sg.hiNote ? ' ' + sg.hiNote : '') + '</span>' +
    (sg.lo != null || sg.hi != null ? ' <button id="applySg" data-k="' + k + '" data-lo="' + (sg.lo ?? '') + '" data-hi="' + (sg.hi ?? '') + '">采用建议</button>' : '') +
    ' <button id="resetOne" data-k="' + k + '">恢复本级推荐值</button>' + ' <span class="dim">推荐: 目标 ' + REC.lv[k].pct + '(锚点 ' + REC.lv[k].anchor + ') / 下限 ' + REC.lv[k].lo + ' / 上限 ' + REC.lv[k].hi + ' / 绝对下限 ' + REC.lv[k].abs + ' ' + ABS(k) + '(规范 ' + REC.lv[k].absSpec + ')' + (REC.lv[k].p90 != null ? ' / 典型上沿 ' + REC.lv[k].p90 : '') + '</span>' + '</div>' +
    '<p class="dim">图上: 竖线 下限(红, 步骤与门禁) / 目标(蓝虚线) / 上限(紫), 横线 绝对下限(橙), 都可按住拖动; 琥珀点线是混档线(目标与弱一档目标的中点, 跟随目标, 只给排查). 散点横轴相对指标, 纵轴绝对指标(' + ABS(k) + '), 实心是参考主题, 空心圈是其他主题: 红区不及目标, 琥珀区偏淡(像弱一档), 紫区超出目标. 点圆点看该实例, 点上方柱子看该区间全部实例.</p>' +
    (st.pick && P.find((x) => x.id === st.pick) ? '<h3>选中的实例</h3><div class="grid">' + card(P.find((x) => x.id === st.pick)) + '</div>' : '');
  h += '<p class="dim">来源键: ' + Object.entries(keys).sort((a, b) => b[1] - a[1]).slice(0, 14).map(([x, n]) => '<code>' + esc(x) + '</code> ' + n).join(' · ') + '</p>';
  const per = {}; P.forEach((x) => { (per[x.theme] ||= [0, 0, 0, 0])[zone(x)]++; });
  h += '<table><tr><th>主题</th><th>不及</th><th>合适</th><th>超出</th><th>偏淡</th><th>中位 %</th><th>最低 %</th></tr>' + D.themes.filter((x) => per[x.file]).map((x) => {
    const v = P.filter((it) => it.theme === x.file).map((it) => it.rd);
    return '<tr><td>' + (isRef(x.file) ? '★ ' : '') + esc(x.label) + '</td>' + per[x.file].map((n, i) => '<td style="color:' + (n && i !== 1 ? ZC[i] : '#777') + '">' + n + '</td>').join('') + '<td>' + r1(med(v)) + '</td><td>' + Math.min(...v) + '</td></tr>';
  }).join('') + '</table>';
  h += '<div style="margin:8px 0">实例: <select id="view"><option value="edge"' + (st.view === 'edge' ? ' selected' : '') + '>上下限两侧</option><option value="bin"' + (st.view === 'bin' ? ' selected' : '') + '>点直方图选区间</option></select></div>';
  if (st.view === 'edge') {
    [[c.lo, '下限'], [c.hi, '上限']].forEach(([v, n]) => {
      const s = [...P].sort((a, b) => Math.abs(a.rd - v) - Math.abs(b.rd - v));
      const below = s.filter((x) => x.rd < v).slice(0, 6).sort((a, b) => a.rd - b.rd), above = s.filter((x) => x.rd >= v).slice(0, 6).sort((a, b) => a.rd - b.rd);
      h += '<h3>' + n + ' ' + v + '%: 左侧 6 个 | 右侧 6 个</h3><div class="grid">' + below.map(card).join('') + '</div><div style="border-top:2px dashed #fff;margin:6px 0"></div><div class="grid">' + above.map(card).join('') + '</div>';
    });
  } else if (st.bin == null) h += '<p class="dim">点直方图上的柱子查看该区间全部实例</p>';
  else {
    const lo = (st.bin / bins) * MAX, hi = ((st.bin + 1) / bins) * MAX;
    const L = P.filter((x) => x.rd >= lo && (x.rd < hi || st.bin === bins - 1)).sort((a, b) => a.rd - b.rd);
    h += '<h3>区间 ' + r1(lo) + '% ~ ' + r1(hi) + '%: ' + L.length + ' 个</h3><div class="grid">' + L.slice(0, 120).map(card).join('') + '</div>';
  }
  return h;
}
function sepPage() {
  const P = pairs(), M = cells(P), gs = Object.keys(GROUPS);
  const cell = (t, k) => M[t]?.[k];
  let h = '<h2>区分度</h2><p class="dim">数值是各主题该级相对指标的中位数之差(百分点). 同组相邻两档要拉开最小档差; 跨组同档要有最小区分度; 不同组不同档不设数值, 到分级矩阵看效果. 推荐值 = 各主题差值掐头去尾后的 P25(不低于 5), 括号里是中位数; 红色 = 低于最小值(负数为档位倒挂).</p>';
  h += '<h3>同组档差(强 - 中, 中 - 弱)</h3><table><tr><th>主题</th>' + gs.flatMap((g) => ['强>中', '中>弱'].map((p) => '<th>' + g + ' ' + p + '</th>')).join('') + '</tr>';
  h += '<tr><td>最小值</td>' + gs.flatMap((g) => ['强>中', '中>弱'].map((p) => { const k = g + p[0] + '>' + p[2]; return '<td><input type="number" step="0.5" data-sep="' + k + '" data-kind="inGroup" value="' + (sepCfg(k, 'inGroup') ?? '') + '"></td>'; })).join('') + '</tr>';
  h += '<tr><td class="dim">推荐</td>' + gs.flatMap((g) => ['强>中', '中>弱'].map((p) => '<td class="dim">' + (REC.inGroup[g + p[0] + '>' + p[2]] ? REC.inGroup[g + p[0] + '>' + p[2]].min + ' (' + REC.inGroup[g + p[0] + '>' + p[2]].med + ')' : '-') + '</td>')).join('') + '</tr>';
  for (const t of D.themes) {
    h += '<tr><td>' + esc(t.label) + '</td>' + gs.flatMap((g) => [['强', '中'], ['中', '弱']].map(([a, b]) => {
      const x = cell(t.file, g + a), y = cell(t.file, g + b);
      if (x === undefined || y === undefined) return '<td class="dim">-</td>';
      const d = r1(x - y), min = sepCfg(g + a + '>' + b, 'inGroup');
      return '<td class="' + (min != null && d < min ? 'bad' : 'good') + '">' + d + '</td>';
    })).join('') + '</tr>';
  }
  h += '</table><h3>跨组同档区分度(|差|)</h3><table><tr><th>主题</th>';
  const pairsX = []; for (const l of LV) for (let i = 0; i < gs.length; i++) for (let j = i + 1; j < gs.length; j++) pairsX.push([gs[i] + l, gs[j] + l]);
  h += pairsX.map(([a, b]) => '<th>' + a + '|' + b + '</th>').join('') + '</tr><tr><td>最小值</td>' +
    pairsX.map(([a, b]) => '<td><input type="number" step="0.5" data-sep="' + a + '|' + b + '" data-kind="cross" value="' + (sepCfg(a + '|' + b, 'cross') ?? '') + '"></td>').join('') + '</tr>' +
    '<tr><td class="dim">推荐</td>' + pairsX.map(([a, b]) => '<td class="dim">' + (REC.cross[a + '|' + b] ? REC.cross[a + '|' + b].min + ' (' + REC.cross[a + '|' + b].med + ')' : '-') + '</td>').join('') + '</tr>';
  for (const t of D.themes) {
    h += '<tr><td>' + esc(t.label) + '</td>' + pairsX.map(([a, b]) => {
      const x = cell(t.file, a), y = cell(t.file, b);
      if (x === undefined || y === undefined) return '<td class="dim">-</td>';
      const d = r1(Math.abs(x - y)), min = sepCfg(a + '|' + b, 'cross');
      return '<td class="' + (min != null && d < min ? 'bad' : 'good') + '">' + d + '</td>';
    }).join('') + '</tr>';
  }
  return h + '</table><button id="resetSep">区分度恢复推荐值</button>';
}
function matrixPage() {
  const P = pairs(), M = cells(P);
  st.mt ||= D.themes[0]?.file;
  let h = '<h2>分级矩阵</h2><p class="dim">每格取该主题该级中位数附近的实例; 不同组不同档不设数值, 在这里看整体层次是否合理. 主题: <select id="mt">' +
    D.themes.map((t) => '<option value="' + t.file + '"' + (t.file === st.mt ? ' selected' : '') + '>' + esc(t.label) + '</option>').join('') + '</select></p><div class="mx"><div></div>' + LV.map((l) => '<div class="h">' + l + '</div>').join('');
  for (const g of Object.keys(GROUPS)) {
    h += '<div class="h">' + g + '</div>';
    for (const l of LV) {
      const k = g + l, m = M[st.mt]?.[k];
      const L = P.filter((x) => x.theme === st.mt && lvOf(x) === k).sort((a, b) => Math.abs(a.rd - m) - Math.abs(b.rd - m)).slice(0, 2);
      h += '<div class="c">' + (m === undefined ? '<span class="dim">无</span>' : '<b>' + r1(m) + '%</b> ' + L.map((x) =>
        (x.crop ? '<img loading="lazy" src="' + x.crop + '">' : '<div class="syn" style="background:' + x.bg + ';color:' + x.fg + '">' + esc((x.texts || [])[0] || 'Aa 示例') + '</div>') + '<span class="dim">' + esc(x.role) + ' ' + x.rd + '%</span>').join('')) + '</div>';
    }
  }
  return h + '</div>';
}
function rulesPage() {
  const P = pairs();
  st.rules ||= null;
  const rules = st.rules || D.saved?.rules || RULES0;
  let h = '<h2>相对约束</h2><p class="dim">放在一起展示的两类内容: 每个主题 a 的相对指标中位数 / b 的 要落在 [最小, 最大].</p>';
  rules.forEach((r, i) => {
    const rows = D.themes.map((t) => { const a = med(P.filter((x) => x.theme === t.file && x.role === r.a).map((x) => x.rd)), b = med(P.filter((x) => x.theme === t.file && x.role === r.b).map((x) => x.rd)); return { t, a, b, q: a / b }; }).filter((x) => !isNaN(x.q));
    const bad = rows.filter((x) => x.q < r.min || x.q > r.max).length;
    h += '<h3>' + esc(r.a) + ' / ' + esc(r.b) + ' <span class="dim">' + esc(r.why) + '</span></h3>最小 <input type="number" step="0.05" data-rule="' + i + '" data-f="min" value="' + r.min + '"> 最大 <input type="number" step="0.05" data-rule="' + i + '" data-f="max" value="' + r.max + '"> ' +
      '<span class="' + (bad ? 'bad' : 'good') + '">' + bad + ' / ' + rows.length + ' 个主题越界</span><table><tr><th>主题</th><th>' + esc(r.a) + '</th><th>' + esc(r.b) + '</th><th>比值</th></tr>' +
      rows.map((x) => '<tr><td>' + esc(x.t.label) + '</td><td>' + r1(x.a) + '</td><td>' + r1(x.b) + '</td><td class="' + (x.q < r.min || x.q > r.max ? 'bad' : 'good') + '">' + x.q.toFixed(2) + '</td></tr>').join('') + '</table>';
  });
  return h + '<p><button id="resetRules">恢复默认约束</button></p>';
}
function render() {
  REC = recommend();
  nav();
  const p = st.page;
  document.getElementById('main').innerHTML = p === 'overview' ? overview() : p === 'sep' ? sepPage() : p === 'matrix' ? matrixPage() : p === 'rules' ? rulesPage()
    : p === 'labeled' ? '<h2>已标注</h2><div class="grid">' + pairs().filter((x) => st.labels[x.id]).sort((a, b) => LEVELS.indexOf(lvOf(a)) - LEVELS.indexOf(lvOf(b)) || a.rd - b.rd).map(card).join('') + '</div>'
    : lvPage(p.slice(3));
}
document.addEventListener('change', (e) => {
  const d = e.target.dataset;
  if (d.lv) { (st.lv[d.lv] ||= {})[d.f] = +e.target.value; }
  else if (d.sep) { st.sep[d.sep] = e.target.value === '' ? null : +e.target.value; }
  else if (d.rule !== undefined) { (st.rules ||= JSON.parse(JSON.stringify(D.saved?.rules || RULES0)))[+d.rule][d.f] = +e.target.value; }
  else if (d.over) { const id = e.target.closest('.card').dataset.id; if (e.target.value) st.over[id] = e.target.value; else delete st.over[id]; }
  else if (e.target.id === 'view') st.view = e.target.value;
  else if (e.target.id === 'mt') st.mt = e.target.value;
  else if (e.target.id === 'exSame') st.exSame = e.target.checked;
  else if (e.target.id === 'recBase') st.recBase = e.target.value;
  save(); render();
});
document.addEventListener('click', (e) => {
  const n = e.target.closest('nav div[data-p]'); const go = e.target.dataset.go;
  if (n || go) { e.preventDefault(); st.page = go || n.dataset.p; st.bin = null; save(); render(); scrollTo(0, 0); return; }
  const d = e.target.dataset;
  if (d.bin !== undefined) { st.bin = +d.bin; st.view = 'bin'; save(); render(); return; }
  if (d.ref !== undefined) { const a = (st.ref ||= [...REF0]); const i = a.indexOf(d.ref); if (i < 0) a.push(d.ref); else a.splice(i, 1); save(); render(); return; }
  if (d.rf !== undefined) { const k = st.page.slice(3); const a = (st.roleF[k] ||= []); const i = a.indexOf(d.rf); if (i < 0) a.push(d.rf); else a.splice(i, 1); save(); render(); return; }
  if (e.target.id === 'applySg') { const c = (st.lv[d.k] ||= {}); if (d.lo) c.lo = +d.lo; if (d.hi) c.hi = +d.hi; save(); render(); return; }
  if (e.target.id === 'resetLv') { st.lv = {}; save(); render(); return; }
  if (e.target.id === 'resetOne') { delete st.lv[d.k]; save(); render(); return; }
  if (d.pt !== undefined) { st.pick = st.pick === d.pt ? null : d.pt; save(); render(); return; }
  if (e.target.id === 'resetSep') { st.sep = {}; save(); render(); return; }
  if (e.target.id === 'resetRules') { st.rules = null; save(); render(); return; }
  const l = e.target.closest('.lb button');
  if (l) { const id = l.closest('.card').dataset.id; if (st.labels[id] === l.dataset.l) delete st.labels[id]; else st.labels[id] = l.dataset.l; save(); render(); return; }
  if (e.target.tagName === 'IMG' && e.target.closest('.card, .mx')) { const z = document.getElementById('zoom'); z.querySelector('img').src = e.target.src; z.style.display = 'flex'; }
});
// 拖动分界线: 拖动中只移动图上的线, 松手后写入并重绘
let drag = null;
document.addEventListener('pointerdown', (e) => {
  const f = e.target.dataset?.drag;
  if (!f) return;
  const svg = e.target.closest('svg');
  drag = { f, svg, k: svg.dataset.k, d: Object.fromEntries(['x0', 'w', 'max', 'y1', 'hs', 'ymax'].map((n) => [n, +svg.dataset[n]])), v: null };
  e.preventDefault();
});
document.addEventListener('pointermove', (e) => {
  if (!drag) return;
  const { d, svg, f } = drag, r = svg.getBoundingClientRect();
  const g = svg.querySelector('[data-g="' + f + '"]');
  if (f === 'abs') {
    const y = Math.min(d.y1 + d.hs, Math.max(d.y1, e.clientY - r.top));
    drag.v = r1(((d.y1 + d.hs - y) / d.hs) * d.ymax);
    g.querySelectorAll('line').forEach((l) => { l.setAttribute('y1', y); l.setAttribute('y2', y); });
    g.querySelector('circle').setAttribute('cy', y);
    const t = g.querySelector('text'); t.setAttribute('y', y + 4); t.textContent = '绝对下限 ' + drag.v + ' ' + ABS(drag.k);
    const z = svg.querySelector('[data-g="zabs"]'); z.setAttribute('y', y); z.setAttribute('height', d.y1 + d.hs - y);
  } else {
    const x = Math.min(d.x0 + d.w, Math.max(d.x0, e.clientX - r.left));
    drag.v = r1(((x - d.x0) / d.w) * d.max);
    g.querySelectorAll('line').forEach((l) => { l.setAttribute('x1', x); l.setAttribute('x2', x); });
    g.querySelector('circle').setAttribute('cx', x);
    const t = g.querySelector('text'); t.setAttribute('x', x + 8); t.textContent = ({ lo: '下限', pct: '目标', hi: '上限' })[f] + ' ' + drag.v + '%';
    if (f === 'lo') svg.querySelector('[data-g="zlo"]').setAttribute('width', x - d.x0);
    if (f === 'hi') { const z = svg.querySelector('[data-g="zhi"]'); z.setAttribute('x', x); z.setAttribute('width', d.x0 + d.w - x); }
  }
});
document.addEventListener('pointerup', () => {
  if (!drag) return;
  const { k, f, v } = drag;
  drag = null;
  if (v == null) return;
  (st.lv[k] ||= {})[f] = v;
  save(); render();
});
document.getElementById('zoom').onclick = () => { document.getElementById('zoom').style.display = 'none'; };
addEventListener('keydown', (e) => { if (e.key === 'Escape') document.getElementById('zoom').style.display = 'none'; });
document.getElementById('submit').onclick = async () => {
  const P = pairs();
  const labels = Object.fromEntries(Object.entries(st.labels).map(([id, v]) => { const it = P.find((x) => x.id === id) || D.items.find((x) => x.id === id); return [id, { label: v, level: it ? lvOf(it) : null, key: it?.key, rd: it?.rd, apca: it?.apca, de: it?.de }]; }));
  const sep = { inGroup: Object.fromEntries(Object.keys(REC.inGroup).map((k) => [k, sepCfg(k, 'inGroup')])), cross: Object.fromEntries(Object.keys(REC.cross).map((k) => [k, sepCfg(k, 'cross')])) };
  const body = { metric: { relative: 'OKLab 明度差 / 本主题正文明度差 x 100', absolute: { 内容: 'APCA Lc', 暗化强: 'APCA Lc', 暗化中: 'APCA Lc', 暗化弱: 'OKLab ΔE x 100', 线条: 'OKLab ΔE x 100', 底色: 'OKLab ΔE x 100' } },
    levels: Object.fromEntries(LEVELS.map((k) => [k, { ...lvCfg(k), mixLo: mixLo(k) }])), recommended: REC, sep, rule: 'v2', ref: st.ref || REF0, recBase: st.recBase || 'ref', overrides: st.over, rules: st.rules || D.saved?.rules || RULES0, labels };
  const res = await fetch('/submit', { method: 'POST', body: JSON.stringify(body) }).then((x) => x.json()).catch(() => null);
  document.getElementById('msg').textContent = res?.ok ? '已提交 ' + res.at : '提交失败(服务没开?)';
};
document.getElementById('exSame').checked = st.exSame !== false;
document.getElementById('recBase').value = st.recBase || 'ref';
async function load() {
  D = await fetch('data.json').then((x) => x.json());
  for (const [k, v] of Object.entries(D.labels || {})) st.labels[k] ??= (typeof v === 'string' ? v : v.label);
  const p = D.progress;
  document.getElementById('prog').textContent = p ? '已普查 ' + p.done.length + ' / ' + p.total + ' 个主题' + (p.running ? ', 普查进行中(点刷新数据)' : '') : '';
  render();
}
document.getElementById('reload').onclick = load;
load();
</script></body></html>`;
