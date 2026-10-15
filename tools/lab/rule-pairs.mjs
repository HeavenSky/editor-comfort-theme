// 普查覆盖不到的颜色键(占位字, 通知, 补全, 悬停, peek, 菜单, 快速输入, diff 等截图场景之外的界面)按语义推出它画在哪个底色键上,
// 以及普查样本为 0 的级(如 线条中)按参考主题的颜色键取值标定门槛. 纯函数, 由 tools/lab/threshold-lab.mjs export 调用, test/levels.test.mjs 覆盖.

// 明确的配对: [键的正则, 底色键...]; 按顺序取第一条命中的, 底色键要在注册表里才用
const EXPLICIT = [
  [/^input\.placeholderForeground$/, 'input.background'],
  [/^(\w+)\.placeholderForeground$/, '$1.background', 'input.background'],
  [/^notification(Link|sErrorIcon|sWarningIcon|sInfoIcon)\.foreground$/, 'notifications.background'],
  [/^notification(s|Toast|Center)\.border$/, 'notifications.background', 'editor.background'],
  [/^notificationCenterHeader\.foreground$/, 'notificationCenterHeader.background', 'notifications.background'],
  [/^peekViewResult\.(file|line)Foreground$/, 'peekViewResult.background'],
  [/^peekViewTitle(Label|Description)\.foreground$/, 'peekViewTitle.background'],
  [/^peekView\.border$/, 'editor.background'],
  [/^peekViewEditor\.matchHighlightBorder$/, 'peekViewEditor.background'],
  [/^peekView(Result|Editor)\.(matchHighlight|selection)Background$/, 'peekView$1.background'],
  [/^peekView(Result|Editor)\.\w*[bB]ackground$/, 'editor.background'],
  [/^peekViewEditor(Gutter|StickyScroll|StickyScrollGutter)\.background$/, 'peekViewEditor.background'],
  [/^menu\.separatorBackground$/, 'menu.background'],
  [/^diffEditor\.(inserted|removed)Text(Background|Border)$/, 'editor.background'],
  [/^diffEditor\.(inserted|removed)LineBackground$/, 'editor.background'],
  [/^diffEditorGutter\.\w+Background$/, 'editorGutter.background', 'editor.background'],
  [/^diffEditor\.unchangedRegionForeground$/, 'diffEditor.unchangedRegionBackground', 'editor.background'],
  [/^diffEditor\.(unchangedRegionBackground|unchangedCodeBackground|diagonalFill|border|move\.border|moveActive\.border)$/, 'editor.background'],
  [/^editorOverviewRuler\.(?!background)\w+$/, 'editorOverviewRuler.background', 'editor.background'],
  [/^(editorIndentGuide|editorBracketPairGuide)\.\w+$/, 'editor.background'],
  [/^debugToolBar\.(background|border)$/, 'editor.background'],
];

// 同前缀没有底色键时, 按所在容器兜底(状态栏项画在状态栏上, 标签画在标签栏上等)
const CONTAINER = { statusBarItem: 'statusBar.background', tab: 'editorGroupHeader.tabsBackground', breadcrumb: 'editor.background', activityBarBadge: 'activityBar.background',
  activityBarTop: 'titleBar.activeBackground', list: 'sideBar.background', tree: 'sideBar.background', sideBarSectionHeader: 'sideBar.background', panelTitle: 'panel.background',
  editorGutter: 'editor.background', editorLineNumber: 'editorGutter.background', editorCodeLens: 'editor.background', editorInlayHint: 'editor.background' };

/**
 * 没有普查配对的键按规则推出底色键. 命名约定只用于字 / 图标 / 线(内容, 暗化, 线条组); 底色键只用明确表(diff, peek 等确实叠在编辑区上的),
 * 因为层次底(标签, 标题栏等)常与编辑区底故意同色, 按约定配到编辑区底会让 level_floor 把它推开, 改掉原设计.
 * @param {string[]} keys 待推的键(已分到 内容 / 暗化 / 线条 / 底色 四组)
 * @param {Set<string>} registry 注册表里的全部颜色键(只采用存在的底色键)
 * @param {(key: string) => string} levelOf 键 -> 级(如 '内容中')
 * @returns {Record<string, string[]>} 键 -> 底色键(按可靠程度排序)
 */
export function rulePairs(keys, registry, levelOf = () => '') {
  const out = {};
  for (const k of keys) {
    if (k === 'editor.background' || k.startsWith('terminal.')) continue;
    let us = null;
    for (const [re, ...unders] of EXPLICIT) {
      const m = k.match(re);
      if (m) { us = unders.map((u) => u.replace(/\$(\d)/g, (_, i) => m[+i])); break; }
    }
    if (!us && !levelOf(k).startsWith('底色')) us = byName(k);
    if (!us) continue;
    const pre = k.split('.')[0];
    if (CONTAINER[pre]) us.push(CONTAINER[pre]);
    us = [...new Set(us.filter((u) => u !== k && registry.has(u)))];
    if (us.length) out[k] = us;
  }
  return out;
}

// 命名约定: X.yyyForeground -> X.yyyBackground, X.background; X.yyyBorder / X.border -> X.background, editor.background;
function byName(k) {
  const i = k.indexOf('.');
  if (i < 0) return [];
  const pre = k.slice(0, i), rest = k.slice(i + 1);
  const fg = rest.match(/^(\w*?)(?:[fF]oreground|IconForeground)$/);
  if (fg) return [`${pre}.${fg[1] ? fg[1] + 'Background' : 'background'}`, `${pre}.background`];
  if (/[bB]order\d?$/.test(rest)) return [`${pre}.background`, 'editor.background'];
  return [];
}

// ---- 按颜色键标定(口径同标定台 recommend: 目标 = 各主题中位数的 20% 截尾均值, 修复下限 = 实例 P5) ----
const sorted = (v) => [...v].sort((a, b) => a - b);
export const median = (v) => { const s = sorted(v), n = s.length; return !n ? NaN : n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
export const tmean = (v) => { const s = sorted(v), c = Math.floor(s.length * 0.2), t = s.length > 4 ? s.slice(c, s.length - c) : s; return t.reduce((a, b) => a + b, 0) / t.length; };
export const quantile = (v, p) => { const s = sorted(v); return s[Math.min(s.length - 1, Math.max(0, Math.round(p * (s.length - 1))))]; };
const r1 = (x) => Math.round(x * 10) / 10;

/**
 * 某一级的按键标定.
 * @param {{theme: string, rd: number, abs: number}[]} samples 参考主题里该级各键的实例(rd 与绝对指标已算好)
 * @param {number} absSpec 绝对下限的规范值
 * @returns {{pct: number, lo: number, abs: number, n: number, themes: number} | null} 无样本返回 null
 */
export function calibrateByKeys(samples, absSpec) {
  if (!samples.length) return null;
  const per = Object.values(samples.reduce((m, s) => ((m[s.theme] ||= []).push(s.rd), m), {}));
  return { pct: r1(tmean(per.map(median))), lo: r1(quantile(samples.map((s) => s.rd), 0.05)),
    abs: Math.min(absSpec, Math.floor(quantile(samples.map((s) => s.abs), 0.05))), n: samples.length, themes: per.length };
}
