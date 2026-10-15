// 颜色键分层: 把 VS Code 颜色键按 组 x 级 自动归类, 给出命中的规则, 供门槛标定台的 /keys 页人工复核.
// 组: 内容(必须读得清的字与图标) / 暗化(刻意压低但要认得出) / 线条(边框, 分隔线, 焦点框, 指示线) / 底色(强调底, 状态底, 层次底);
//   每组分 强 / 中 / 弱. 另有 基准(editor.background, 一切比较的参照)与 不适用(阴影等).
// 状态标记: 禁用(归本组的弱, 不跨组), 非活动(失焦 / 未选中), 悬停, 选中 / 激活; 语义: 靠色相表达含义(错误 / 警告, git, diff, 终端色等).
// 规则按顺序取第一条命中的; 依据只看键名, 复核时以键在界面上的实际用途为准.
export const GROUPS = ['内容', '暗化', '线条', '底色'];
export const LEVELS = ['强', '中', '弱'];

const SEM = /(error|warning|info|hint|success|added|deleted|modified|removed|inserted|conflict|untracked|ignored|renamed|stage|submodule|ansi|charts\.|symbolIcon|bracketHighlight|debugToken|debugIcon|testing\.|gitDecoration|merge|diff|minimapGutter|scmGraph)/i;

// [组, 级, 正则, 说明]; 正则对完整键名
const RULES = [
  // ---- 特殊 ----
  ['基准', '', /^editor\.background$/, '编辑区底色, 一切比较的参照'],
  ['不适用', '', /shadow|opacity$|Opacity$|Glow$|Shimmer$|\.retired$/i, '阴影, 透明度系数, 动效光晕, 已退役键: 不参与对比分级'],
  ['不适用', '', /^inlineChat\.regionHighlight$/, '无效键: VS Code 1.91 起已移除的旧键'],
  ['不适用', '', /^(meta|source|string|punctuation|keyword|entity|variable|support|constant|storage|comment|markup)\./, '无效键: 原主题误写进 colors 的 TextMate 语法作用域'],
  ['不适用', '', /^list\.dropBetweenBackground$/, '只在拖拽列表项时出现的插入线, 普查测不到真实状态, 不参与分级'],
  // ---- 按普查实测与语义复核的逐键规则(优先于下面的通用规则) ----
  ['底色', '强', /^(editor|terminal)\.findMatchBackground$/, '复核: 当前匹配项要比其他匹配更醒目'],
  ['底色', '中', /^(editor|terminal)\.findMatchHighlightBackground$/, '复核: 其他匹配项要被看出来, 与选区同档(GitHub Dark 实测 61%)'],
  ['线条', '强', /^editorGutter\.(added|modified|deleted)\w*Background$/, '复核: 行号槽 git 标记是语义标记, 与诊断波浪线同样要醒目'],
  ['内容', '中', /^(titleBar|commandCenter|panelTitle)\.activeForeground$/, '复核: 这里的 active 是窗口 / 面板聚焦状态, 不是选中项'],
  ['内容', '中', /^list\.focusForeground$/, '复核: 键盘焦点行, 不是选中行(选中行文字仍归内容强)'],
  ['内容', '中', /^statusBar\.foreground$/, '复核: 状态栏是常驻的主要信息, 参考主题实测 96%'],
  // ---- 禁用: 归本组的弱 ----
  ['?', '弱', /disabled/i, '禁用: 归本组的弱'],
  // ---- 暗化 ----
  ['暗化', '强', /placeholderForeground$|editorGhostText\.foreground$|editorInlayHint\.(foreground|typeForeground|parameterForeground)$|editorCodeLens\.foreground$/, '占位字, 幽灵文字, 内联提示, CodeLens'],
  ['暗化', '弱', /editorWhitespace\.foreground$|editorLineNumber\.dimmedForeground$/, '空白符, 末行之后变淡的行号等最淡的标记'],
  ['暗化', '中', /^editorLineNumber\.foreground$|^activityBar\.inactiveForeground$|gitDecoration\.ignoredResourceForeground$|\.deemphasizedForeground$|foldPlaceholderForeground$/, '行号, 未选中活动栏图标, 被忽略文件, 折叠占位'],
  // ---- 线条 ----
  ['线条', '强', /^editor(Error|Warning|Info|Hint)\.(foreground|border)$/, '诊断波浪线(语义)'],
  ['线条', '强', /focusBorder$|focusOutline$|focusAndSelectionOutline$|activeBorder(Top|Bottom)?$|activeOutline$|contrastActiveBorder$|selectedBorder(Top)?$|\.activeFocusBorder$|findMatchBorder$|editorCursor\.foreground$|selectionHighlightBorder$|cellInsertionIndicator$/, '焦点框, 活动指示线, 光标, 当前匹配描边'],
  ['线条', '中', /^(input|dropdown|checkbox|button|radio|inputOption|settings\.\w+Input|settings\.checkbox|settings\.dropdown|editorWidget|quickInput|menu|notifications|keybindingLabel)\.?\w*Border$|editorIndentGuide\.activeBackground|editorBracketPairGuide\.activeBackground|editorGutter\.(added|modified|deleted)\w*Background$|[oO]utline$|modifiedItemIndicator$|BorderColor\d$/, '控件与浮层边框, 悬停描边, 当前缩进线, 行号槽 git 标记'],
  ['线条', '弱', /border$|Border\d?$|separator$|Separator$|sash|editorIndentGuide\.background|editorBracketPairGuide\.background|editorRuler\.foreground|tree\.indentGuidesStroke|Underline$|\.stroke$|Stroke$|editorOverviewRuler\.border|^tab\.divider$|Border(Top|Bottom)$/, '分隔线, 面板边框, 缩进线, 标尺'],
  ['线条', '中', /^(editorOverviewRuler\.(?!background)\w+|minimap\.\w*Highlight|editorMinimap\.\w+|minimapGutter\.\w+|mergeEditor\.conflict\.\w+\.minimapOverViewRuler|minimap\.chatEditHighlight)$/, '概览标尺与小地图上的标记'],
  // ---- 底色 ----
  ['底色', '强', /[bB]adge\w*\.background$|^button\.\w*[bB]ackground$|^extensionButton\.\w*[bB]ackground$|^progressBar\.background$|^statusBar\.(debugging|noFolder)Background$|^statusBarItem\.(remote|offline|prominent|error|warning)\w*Background$|^inputOption\.activeBackground$|^checkbox\.selectedBackground$/, '强调底: 徽标, 按钮, 进度条, 调试 / 远程状态栏'],
  ['底色', '中', /activeSelectionBackground$|(?<!inactive)selectionBackground$|(?<!inactive)SelectionBackground$|focusBackground$|selectedBackground$|activeBackground$|findMatchBackground$|(?<!Highlight)wordHighlightStrongBackground$|activeSelection\w*Background$|scrollbarSlider\.activeBackground$|\.(inserted|removed)TextBackground$|^inlineChatDiff\.(inserted|removed)$|valueChangedHighlight$/, '状态底: 选中, 聚焦, 当前匹配, diff 改动文字'],
  ['底色', '弱', /background$|Background\d?$|\.fill$|Fill$/i, '层次底: 区块底色, 悬停, 失焦选中, 高亮, 其他匹配'],
  ['内容', '中', /^(editorBracketHighlight|scmGraph|debugTokenExpression|testing\.(icon|runAction)|commentsView\.\w+Icon|terminalSymbolIcon|chart\.)|^success$/, '语义前景: 括号配色, 提交图, 调试值, 测试图标'],
  // ---- 内容 ----
  ['内容', '强', /^editorLineNumber\.activeForeground$|^activityBar\.(foreground|activeForeground)$|activeSelectionForeground$|(?<!inactive)selectionForeground$|focusForeground$|highlightForeground$|focusHighlightForeground$|activeForeground$|selectedForeground$|^tab\.activeForeground$|^list\.highlightForeground$/, '当前 / 选中 / 激活态的字与图标, 匹配高亮字'],
  ['内容', '弱', /descriptionForeground$|inactiveForeground$|unfocused\w*Foreground$|inactiveSelectionForeground$|^(statusBar|titleBar|sideBarTitle|panelTitle|sideBarSectionHeader|editorGroupHeader|tab|breadcrumb)\.foreground$|^tab\.unfocused\w*Foreground$/, '界面辅助文字: 描述, 非活动, 失焦, 标题栏, 状态栏'],
  ['内容', '中', /foreground$|Foreground\d?$|^foreground$|^icon\.foreground$|Color$|^terminal\.ansi|^charts\.|\.(red|green|blue|yellow|orange|purple|lines|foreground)$/, '正文与代码, 图标, 一般前景'],
];

// 复核建议: 自动规则不改, 复核页显示为可一键采用的建议; 依据普查实测
export const SUGGEST = {};

const typeGroup = (k) => (/border|separator|outline|stroke|sash/i.test(k) ? '线条' : /background|fill/i.test(k) ? '底色' : '内容');

export function classify(key) {
  const states = [];
  if (/disabled/i.test(key)) states.push('禁用');
  if (/inactive|unfocused|deemphasized/i.test(key)) states.push('非活动');
  if (/hover/i.test(key)) states.push('悬停');
  if (/(active|selection|selected|focus|current)(?!.*inactive)/i.test(key) && !/inactive|unfocused/i.test(key)) states.push('选中 / 激活');
  const sem = SEM.test(key);
  for (const [g, l, re, why] of RULES) {
    if (!re.test(key)) continue;
    if (g === '?') return { group: typeGroup(key), level: l, states, sem, why };
    // 悬停 / 失焦选中 的底色归 层次底(弱); 失焦的 线 / 字 降一级
    if (g === '底色' && l === '中' && /hover|inactive/i.test(key)) return { group: g, level: '弱', states, sem, why: '悬停 / 失焦的状态底: 归层次底' };
    // 失焦 / 非活动的 强(活动边框, 选中字)降到本组的弱
    if (l === '强' && /inactive|unfocused/i.test(key)) return { group: g, level: '弱', states, sem, why: why + '; 失焦 / 非活动: 降到本组的弱' };
    return { group: g, level: l, states, sem, why };
  }
  return { group: '未归类', level: '', states, sem, why: '没有命中规则' };
}

// ======== 复核页数据: 注册表未废弃的键 + 原主题用到但不在注册表的键; 每个键带自动归类, 16 套原主题里定义它的个数, 各主题全关档的取值 ========
// effective: 主题 -> { 键: 实际取值 }(普查记录, 含 VS Code 推导的默认值); defaults: 自带主题 -> { 键: 取值 }; docs: 键 -> { description, defaults }
export function keysData({ registry, originals, fulls, saved, effective = {}, defaults = {}, docs = {} }) {
  const used = new Map();
  for (const t of Object.values(originals)) for (const k of Object.keys(t?.colors || {})) used.set(k, (used.get(k) || 0) + 1);
  const keys = [...new Set([...Object.keys(registry).filter((k) => !registry[k].deprecated), ...used.keys()])].sort();
  return {
    themes: Object.keys(fulls),
    saved: saved || null,
    systemThemes: Object.keys(defaults),
    keys: keys.map((k) => ({
      key: k, ...classify(k), suggest: SUGGEST[k] || null, used: used.get(k) || 0, reg: !!registry[k], transparent: !!registry[k]?.transparent,
      values: Object.fromEntries(Object.entries(fulls).map(([f, t]) => [f, t?.colors?.[k] || null])),
      effective: Object.fromEntries(Object.entries(effective).map(([f, v]) => [f, v?.[k] || null])),
      system: Object.fromEntries(Object.entries(defaults).map(([f, v]) => [f, v?.[k] || null])),
      doc: docs[k]?.description || null, docDefaults: docs[k]?.defaults || null,
    })),
  };
}

export const KEYS_PAGE = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>颜色键分层复核</title>
<style>
body{margin:0;font:13px/1.5 -apple-system,"PingFang SC",sans-serif;background:#1b1d22;color:#ddd}
header{position:sticky;top:0;z-index:10;background:#24272e;padding:8px 14px;border-bottom:1px solid #3a3e48;display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center}
header b{color:#fff} select,input{background:#30343c;color:#ddd;border:1px solid #4a4f5a;border-radius:4px;padding:1px 5px}
button{background:#30343c;color:#ddd;border:1px solid #4a4f5a;border-radius:4px;padding:2px 10px;cursor:pointer} button.pri{background:#3d6fb6;color:#fff;border-color:#3d6fb6}
.dim{color:#8a93a0} main{padding:8px 14px}
table{border-collapse:collapse;width:100%} td,th{padding:3px 6px;border-bottom:1px solid #2c3038;text-align:left;vertical-align:middle;font-size:12px}
th{position:sticky;top:42px;background:#24272e} tr.ch td{background:#232a36} tr.gh td{background:#2f3542;color:#fff;font-weight:600;font-size:13px}
code{color:#e6c07b} .why{color:#8a93a0} .tag{display:inline-block;padding:0 5px;border-radius:3px;font-size:11px;margin-right:3px;background:#3a3e48}
.tag.sem{background:#5a3d6a} .tag.chg{background:#7a5a20} button.sg{padding:0 6px;font-size:11px;background:#2f5a3a;border-color:#3b8f5a}
.sw{display:inline-block;width:12px;height:12px;border:1px solid #666;margin:0 1px;position:relative;cursor:pointer;vertical-align:-2px}
.sw.none{background:repeating-linear-gradient(45deg,#333 0 2px,#222 2px 4px)} .sw.eff{border:1px dashed #bbb;opacity:.55} .sys .sw{width:14px;height:14px}
.doc{color:#cfd6e0} td.why{max-width:420px}
.sw:hover::after{content:attr(data-t);position:absolute;z-index:20;left:16px;top:-50px;width:110px;height:110px;background:inherit;border:2px solid #fff;
 box-shadow:0 4px 16px #000a;color:#fff;font:11px monospace;display:flex;align-items:flex-end;padding:3px;box-sizing:border-box;text-shadow:0 0 3px #000,0 0 3px #000;white-space:pre-wrap}
</style></head><body>
<header><b>颜色键分层复核</b><a href="/" style="color:#7ab">返回标定台</a>
<label>组 <select id="fG"><option value="">全部</option></select></label>
<label>级 <select id="fL"><option value="">全部</option><option>强</option><option>中</option><option>弱</option></select></label>
<label>范围 <select id="fU"><option value="used">原主题用到的</option><option value="">全部注册表键</option></select></label>
<label>只看 <select id="fO"><option value="">全部</option><option value="chg">已改的</option><option value="sem">语义色</option><option value="dis">禁用</option><option value="ina">非活动</option><option value="un">未归类</option><option value="sg">有建议的</option></select></label>
<input id="fT" placeholder="搜键名 / 说明" size="22">
<label title="关: 主题没定义的键显示 VS Code 按默认规则推导出的实际值(虚线框); 开: 只显示主题自己定义的值"><input type="checkbox" id="onlyDef"> 只展示已定义</label>
<span id="cnt" class="dim"></span><button class="pri" id="submit">提交复核结果</button><span id="msg" class="dim"></span></header>
<main><p class="dim">规则只看键名; 复核时按键在界面上的实际用途改. 禁用归本组的弱, 不跨组. 色块: 16 套主题全关档的取值; 主题没定义的显示 VS Code 推导出的实际值(虚线框, 来自普查), 打开"只展示已定义"后显示为斜纹; 悬停放大.
系统默认: VS Code 自带的 Dark Modern / Light Modern / Dark+ / Light+ 下的实际值. 说明: VS Code 注册颜色键时的官方说明(有数据时显示).
组内顺序 强 > 中 > 弱; 语义 = 靠色相表达含义, 照常分级. 结果按键存在浏览器本地, 提交写到标定目录的 key-levels.json.</p>
<table id="tb"></table></main>
<script>
const OPTS = ['内容强', '内容中', '内容弱', '暗化强', '暗化中', '暗化弱', '线条强', '线条中', '线条弱', '底色强', '底色中', '底色弱', '基准', '不适用', '未归类'];
const LS = 'key-levels';
let D, st = JSON.parse(localStorage.getItem(LS) || '{}');
st.over ||= {};
const save = () => localStorage.setItem(LS, JSON.stringify(st));
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const auto = (k) => k.group + k.level;
const cur = (k) => st.over[k.key] || D.saved?.overrides?.[k.key] || auto(k);
function render() {
  const g = fG.value, l = fL.value, u = fU.value, o = fO.value, q = fT.value.toLowerCase();
  const list = D.keys.filter((k) => {
    const c = cur(k);
    if (u === 'used' && !k.used) return false;
    if (g && !c.startsWith(g)) return false;
    if (l && !c.endsWith(l)) return false;
    if (o === 'chg' && c === auto(k)) return false;
    if (o === 'sem' && !k.sem) return false;
    if (o === 'dis' && !k.states.includes('禁用')) return false;
    if (o === 'ina' && !k.states.includes('非活动')) return false;
    if (o === 'un' && c !== '未归类') return false;
    if (o === 'sg' && !k.suggest) return false;
    return !q || (k.key + ' ' + k.why + ' ' + (k.doc || '')).toLowerCase().includes(q);
  }).sort((a, b) => OPTS.indexOf(cur(a)) - OPTS.indexOf(cur(b)) || a.key.localeCompare(b.key));
  const chg = D.keys.filter((k) => cur(k) !== auto(k)).length;
  cnt.textContent = '显示 ' + list.length + ' 个键 · 已改 ' + chg;
  const only = st.onlyDef;
  const cellOf = (k, t) => {
    const v = k.values[t], e = k.effective?.[t];
    if (v) return '<span class="sw" style="background:' + v + '" data-t="' + esc(t + '\\n' + v) + '"></span>';
    if (!only && e) return '<span class="sw eff" style="background:' + e + '" data-t="' + esc(t + '\\n未定义, 推导值\\n' + e) + '"></span>';
    return '<span class="sw none" data-t="' + esc(t + '\\n未定义') + '"></span>';
  };
  let h = '<tr><th>键</th><th>归类</th><th>标记</th><th>原主题</th><th>16 套取值</th><th>系统默认</th><th>说明 / 依据</th></tr>', last = '';
  for (const k of list) {
    const c = cur(k);
    if (c !== last) { last = c; h += '<tr class="gh"><td colspan="7">' + c + ' <span class="dim">' + list.filter((x) => cur(x) === c).length + '</span></td></tr>'; }
    h += '<tr class="' + (c !== auto(k) ? 'ch' : '') + '"><td><code>' + esc(k.key) + '</code>' + (k.reg ? '' : ' <span class="tag">不在注册表</span>') + '</td>' +
      '<td><select data-k="' + esc(k.key) + '">' + OPTS.map((x) => '<option' + (x === c ? ' selected' : '') + '>' + x + '</option>').join('') + '</select>' + (c !== auto(k) ? ' <span class="tag chg">原 ' + auto(k) + '</span>' : '') + (k.suggest && c !== k.suggest[0] ? ' <button class="sg" data-sg="' + esc(k.key) + '" title="' + esc(k.suggest[1]) + '">建议 ' + k.suggest[0] + '</button>' : '') + '</td>' +
      '<td>' + (k.sem ? '<span class="tag sem">语义</span>' : '') + k.states.map((s) => '<span class="tag">' + s + '</span>').join('') + (k.transparent ? '<span class="tag">需半透明</span>' : '') + '</td>' +
      '<td>' + k.used + '/16</td><td>' + D.themes.map((t) => cellOf(k, t)).join('') + '</td>' +
      '<td class="sys">' + (D.systemThemes || []).map((t) => k.system?.[t] ? '<span class="sw" style="background:' + k.system[t] + '" data-t="' + esc(t + '\\n' + k.system[t]) + '"></span>' : '<span class="sw none" data-t="' + esc(t + '\\n无') + '"></span>').join('') + '</td>' +
      '<td class="why">' + (k.doc ? '<div class="doc">' + esc(k.doc) + '</div>' : '') + (k.docDefaults ? '<div class="dim">默认: ' + esc(Object.entries(k.docDefaults).filter(([, v]) => v != null).map(([m, v]) => m + ' ' + (typeof v === 'string' ? v : JSON.stringify(v))).join(' · ')) + '</div>' : '') + '<div class="dim">归类依据: ' + esc(k.why) + '</div></td></tr>';
  }
  tb.innerHTML = h;
}
document.addEventListener('change', (e) => {
  const k = e.target.dataset.k;
  if (k) { const it = D.keys.find((x) => x.key === k); if (e.target.value === auto(it)) delete st.over[k]; else st.over[k] = e.target.value; save(); }
  render();
});
fT.addEventListener('input', render);
onlyDef.checked = !!st.onlyDef;
onlyDef.addEventListener('change', () => { st.onlyDef = onlyDef.checked; save(); render(); });
document.addEventListener('click', (e) => {
  const k = e.target.dataset.sg;
  if (!k) return;
  const it = D.keys.find((x) => x.key === k);
  st.over[k] = it.suggest[0]; if (st.over[k] === auto(it)) delete st.over[k]; save(); render();
});
submit.onclick = async () => {
  const overrides = { ...(D.saved?.overrides || {}), ...st.over };
  for (const k of D.keys) if (overrides[k.key] === auto(k)) delete overrides[k.key];
  const levels = Object.fromEntries(D.keys.map((k) => [k.key, overrides[k.key] || auto(k)]));
  const r = await fetch('/keys-submit', { method: 'POST', body: JSON.stringify({ overrides, levels }) }).then((x) => x.json()).catch(() => null);
  msg.textContent = r?.ok ? '已提交 ' + r.at + ', 改动 ' + Object.keys(overrides).length + ' 个' : '提交失败(服务没开?)';
};
(async () => {
  D = await fetch('keys.json').then((x) => x.json());
  for (const g of ['内容', '暗化', '线条', '底色', '基准', '不适用', '未归类']) fG.insertAdjacentHTML('beforeend', '<option>' + g + '</option>');
  render();
})();
</script></body></html>`;
