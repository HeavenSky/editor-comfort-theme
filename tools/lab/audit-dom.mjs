// 看不清 / 刺眼排查的页面检查钩子: 由 tools/shoot/shoot.mjs 在每张截图后调用(任务里写 "audit": "tools/lab/audit-dom.mjs"), 在同一画面上逐个元素算颜色.
// 查: 文字与图标(按钮, 徽标, 标签, 输入框等)对叠加后底色的对比度; 边框, 分隔线, 焦点描边与相邻底色的区分度; 选中 / 查找等高亮底看不看得出;
//     大块高饱和亮色底, 贯穿的高饱和亮线, 霓虹徽标等刺眼项. 编辑区代码 token(语法色另有门禁), 小地图与终端画布不在此列.
// 来源: 先按样式表里引用 var(--vscode-*) 的规则匹配元素, 留下值与实际颜色相等的变量; 匹配不到再按值反查工作台上的同色变量.
// 输出: <dir>/audit/<name>.json 与每个问题一张局部截图 <dir>/audit/<name>-<序号>.png(问题位置加虚线框)
import fs from 'node:fs';
import path from 'node:path';

const MAX_ITEMS = 60;
const PAD = 28;

// 页面内执行: 只能用浏览器 API, 不能引用外层变量
function inspect() {
  const parse = (s) => {
    const m = s && s.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null;
  };
  const over = (top, under) => {
    const a = top[3];
    return [0, 1, 2].map((i) => top[i] * a + under[i] * (1 - a)).concat(1);
  };
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  const cr = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const oklch = (c) => {
    const [r, g, b] = c.map((v, i) => (i < 3 ? lin(v) : v));
    const l = Math.cbrt(0.4122214708 * r + 0.5363137080 * g + 0.0514459929 * b);
    const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    const L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s;
    const A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s;
    const B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s;
    return { L, C: Math.hypot(A, B) };
  };
  const hex = (c) => '#' + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();
  const rawHex = (c) => hex(c) + (c[3] < 1 ? Math.round(c[3] * 255).toString(16).padStart(2, '0').toUpperCase() : '');
  // 颜色统一成小写 #rrggbb(aa): 计算样式是 rgb(), 自定义属性里是主题原写法(#RRGGBB / #RRGGBBAA)
  const norm = (s) => {
    s = (s || '').trim().toLowerCase();
    const c = parse(s);
    if (c) return rawHex(c).toLowerCase();
    const m = s.match(/^#([0-9a-f]{3,8})$/);
    if (!m) return s;
    const h = m[1].length <= 4 ? [...m[1]].map((x) => x + x).join('') : m[1];
    return '#' + (h.endsWith('ff') && h.length === 8 ? h.slice(0, 6) : h);
  };

  const wb = document.querySelector('.monaco-workbench');
  const wst = getComputedStyle(wb);
  // 自定义属性取到的是主题原写法(#RRGGBB), 不是 rgb(); 只认 rgb() 会落到兜底色, 浅色主题被当成深色
  const hexRgb = (s) => { const m = (s || '').trim().match(/^#([0-9a-f]{6})/i); return m ? [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16)).concat(1) : null; };
  const base = parse(wst.getPropertyValue('--vscode-editor-background')) || hexRgb(wst.getPropertyValue('--vscode-editor-background')) || [30, 30, 30, 1];
  const dark = lum(base) < 0.2;
  const W = innerWidth, H = innerHeight;

  // 工作台上的颜色变量: 值 -> 键(反查用), 键 -> 值
  const varVal = {};
  for (const sh of document.styleSheets) {
    let rules; try { rules = sh.cssRules; } catch { continue; }
    for (const r of rules) {
      if (!r.style) continue;
      for (let i = 0; i < r.style.length; i++) if (r.style[i].startsWith('--vscode-')) varVal[r.style[i]] = 1;
    }
  }
  for (let i = 0; i < wb.style.length; i++) if (wb.style[i].startsWith('--vscode-')) varVal[wb.style[i]] = 1;
  const byValue = {};
  for (const v of Object.keys(varVal)) {
    const k = norm(wst.getPropertyValue(v));
    if (k) (byValue[k] = byValue[k] || []).push(v);
  }
  // 引用颜色变量的样式规则
  const colorRules = [];
  const walk = (rules) => {
    for (const r of rules) {
      if (r.cssRules && !r.selectorText) { walk(r.cssRules); continue; }
      if (!r.selectorText || !r.style) continue;
      const props = {};
      for (let i = 0; i < r.style.length; i++) {
        const p = r.style[i];
        if (!/color|background|border|outline|shadow/.test(p)) continue;
        const vs = (r.style.getPropertyValue(p).match(/--vscode-[\w-]+/g) || []);
        if (vs.length) props[p] = vs;
      }
      if (Object.keys(props).length) colorRules.push({ sel: r.selectorText, props });
    }
  };
  for (const sh of document.styleSheets) { try { walk(sh.cssRules); } catch {} }
  const keyOf = (v) => v.replace(/^--vscode-/, '').replace(/-/g, '.');
  // 元素某类属性(color / background / border / outline)的来源键: 规则引用且值等于实际颜色的变量优先, 再按值反查; tools/lab/census-dom.mjs 有同一套做法, 两边改动要同步
  const sourceOf = (el, kind, actual, pseudo) => {
    const want = norm(actual);
    const hit = new Set();
    const st = getComputedStyle(el);
    for (const r of colorRules) {
      const sels = r.sel.split(',').map((x) => x.trim()).filter((x) => (pseudo ? x.includes(pseudo) : !/::?(before|after)/.test(x)));
      if (!sels.length) continue;
      const ok = sels.some((x) => { try { return el.matches(x.replace(/::?(before|after)/g, '').replace(/:(hover|active)/g, '') || '*'); } catch { return false; } });
      if (!ok) continue;
      for (const [p, vs] of Object.entries(r.props)) {
        if (kind === 'color' ? p !== 'color' : !p.startsWith(kind)) continue;
        for (const v of vs) if (norm(st.getPropertyValue(v).trim()) === want) hit.add(v);
      }
    }
    const inline = el.getAttribute('style') || '';
    for (const v of inline.match(/--vscode-[\w-]+/g) || []) if (norm(st.getPropertyValue(v).trim()) === want) hit.add(v);
    let keys = [...hit].map(keyOf);
    let how = 'rule';
    if (!keys.length) { keys = rank(el, kind, (byValue[want] || []).map(keyOf)); how = keys.length ? 'value' : 'none'; }
    return { keys: [...new Set(keys)].slice(0, 6), how };
  };

  // 按值反查到的同色键: 按所在区域与属性类型打分, 只留最高分的一批
  const AREA = {
    sidebar: ['sideBar', 'list', 'tree', 'gitDecoration', 'scm', 'input', 'search'], auxiliarybar: ['sideBar', 'list'],
    panel: ['panel', 'problems', 'list', 'terminal', 'input', 'dropdown'], editor: ['editor', 'tab', 'breadcrumb', 'editorGroup', 'editorGutter', 'editorLineNumber'],
    activitybar: ['activityBar'], statusbar: ['statusBar'], titlebar: ['titleBar', 'commandCenter'],
  };
  // 按值反查只留与属性类型相符的键: 字色只认前景类, 填充只认底色类, CSS 边框只认边框 / 线条类; 同色的别类键会把文字认成底色键
  const KIND_OK = { color: /foreground|Foreground\d?$|Color$|^foreground$|^terminal\.ansi/, background: /background|Background\d?$/, border: /border|Border|outline|Outline|stroke|Stroke|separator|sash/, outline: /border|Border|outline|Outline/ };
  const rank = (el, kind, keys) => {
    keys = keys.filter((k) => !KIND_OK[kind] || KIND_OK[kind].test(k));
    if (keys.length < 2) return keys;
    const area = (el.closest('[id^="workbench.parts."]')?.id || '').replace('workbench.parts.', '');
    const pre = AREA[area] || [];
    const suf = kind === 'color' ? /foreground$/i : kind === 'background' ? /background$/i : /border|outline/i;
    const score = (k) => (pre.some((p) => k.startsWith(p + '.') || k.startsWith(p)) ? 2 : 0) + (suf.test(k) ? 1 : 0)
      - (/^(agent|chat|notebook|testing|debug|inlineChat|interactive|merge|diffEditor|minimap|walkThrough|welcome|extension|settings|keybinding|ports|profile|commentsView|gauge|simpleFind|radio|toolbar|editorHoverWidget|editorStickyScroll)/.test(k) ? 1 : 0);
    const best = Math.max(...keys.map(score));
    return keys.filter((k) => score(k) === best);
  };
  const opacityOf = (el) => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= +getComputedStyle(e).opacity; return o; };
  // 某点之下(从 el 起往下)叠出的底色, 以及最上层出底色的元素
  const bgAt = (x, y, el) => {
    const stack = document.elementsFromPoint(Math.min(W - 1, Math.max(0, x)), Math.min(H - 1, Math.max(0, y)));
    let i = el ? stack.findIndex((e) => e === el || e.contains(el) ) : 0;
    if (i < 0) {
      // el 不接收指针事件时不在栈里: 退回祖先链
      const chain = [];
      for (let e = el; e && e.nodeType === 1; e = e.parentElement) chain.push(e);
      return compose(chain);
    }
    return compose(stack.slice(i));
  };
  const compose = (list) => {
    let c = base, src = null;
    for (const e of [...list].reverse()) {
      const b = parse(getComputedStyle(e).backgroundColor);
      if (b && b[3] > 0.01) { c = over(b, c); src = e; }
    }
    return { c, src };
  };
  const visible = (el, r) => {
    if (r.width < 2 || r.height < 2 || r.right < 0 || r.bottom < 0 || r.left > W || r.top > H) return false;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none') return false;
    const cx = Math.min(W - 1, Math.max(0, r.left + r.width / 2)), cy = Math.min(H - 1, Math.max(0, r.top + r.height / 2));
    const top = document.elementFromPoint(cx, cy);
    return !!top && (el.contains(top) || top.contains(el));
  };
  const label = (el) => {
    const t = (el.getAttribute('aria-label') || el.title || el.textContent || '').trim().replace(/\s+/g, ' ');
    const cls = (el.className && typeof el.className === 'string' ? el.className : '').split(/\s+/).filter(Boolean).slice(0, 3).join('.');
    const area = el.closest('[id^="workbench.parts."], .part')?.id?.replace('workbench.parts.', '') || '';
    return { text: t.slice(0, 60), path: `${area} ${el.tagName.toLowerCase()}${cls ? '.' + cls : ''}`.trim() };
  };
  const skip = (el) => el.closest('.view-lines, .minimap, .xterm, .monaco-aria-container, .context-view-pointerBlock, .overlayWidgets .find-widget[aria-hidden="true"]');
  const rect = (r) => ({ x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) });

  const items = [];
  const add = (it) => items.push(it);
  const els = [...wb.querySelectorAll('*')];
  for (const el of els) {
    if (skip(el) || el.closest('.colorpicker-color-decoration')) continue;
    const r = el.getBoundingClientRect();
    if (!visible(el, r)) continue;
    const st = getComputedStyle(el);
    const lb = label(el);
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;

    // ---- 文字 / 图标 ----
    const txt = [...el.childNodes].filter((n) => n.nodeType === 3 && n.textContent.trim());
    const icon = /\bcodicon\b/.test(el.className) && getComputedStyle(el, '::before').content !== 'none';
    if (txt.length || icon) {
      let tr = r;
      if (txt.length) { const rg = document.createRange(); rg.selectNodeContents(txt[0]); const q = rg.getBoundingClientRect(); if (q.width > 1) tr = q; }
      const fg0 = parse(st.color);
      const op = opacityOf(el);
      // 透明的(悬停才出现的折叠箭头, 非活动标签的关闭按钮等)不算
      if (fg0 && fg0[3] * op > 0.05) {
        const { c: bg, src } = bgAt(tr.left + tr.width / 2, tr.top + tr.height / 2, el);
        const fg = over([...fg0.slice(0, 3), fg0[3] * op], bg);
        const ratio = cr(fg, bg);
        const big = parseFloat(st.fontSize) >= 18.6 || (parseFloat(st.fontSize) >= 14 && +st.fontWeight >= 700);
        const lineNo = !!el.closest('.line-numbers, .margin-view-overlays');
        const lo = lineNo ? [2.2, 3] : icon || big ? [2, 3] : [3, 4.5];
        const k = oklch(fg);
        let level = null, kind = lineNo ? '行号' : icon ? '图标' : '文字';
        if (ratio < lo[0]) level = '看不清';
        else if (ratio < lo[1]) level = '偏淡';
        else if (k.C >= 0.15 && ratio >= 10) { level = '偏刺眼'; kind = icon ? '图标高饱和' : '文字高饱和'; }
        if (level) {
          const inBadge = el.closest('.badge, .monaco-count-badge, .badge-content, .activity-item .badge');
          const inBtn = el.closest('.monaco-button, .monaco-text-button');
          const off = el.closest('.disabled, [aria-disabled="true"], :disabled') ? '(禁用)' : '';
          add({
            kind: (inBadge ? `徽标${kind}` : inBtn ? `按钮${kind}` : kind) + off, level, ratio: +ratio.toFixed(2),
            fg: hex(fg), bg: hex(bg), fgRaw: rawHex(fg0), opacity: +op.toFixed(2),
            fgSrc: sourceOf(el, 'color', st.color), bgSrc: src ? sourceOf(src, 'background', getComputedStyle(src).backgroundColor) : { keys: [], how: 'none' },
            rect: rect(tr), ...lb,
          });
        }
      }
    }

    // ---- 边框 / 分隔线 / 焦点描边(含 ::before / ::after 画的线) ----
    const lines = [];
    for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
      const w = parseFloat(st[`border${side}Width`]), c = parse(st[`border${side}Color`]);
      if (w >= 1 && c && c[3] > 0.02 && st[`border${side}Style`] !== 'none') lines.push({ side, c, w, prop: 'border', el, pseudo: null });
    }
    if (st.outlineStyle !== 'none' && parseFloat(st.outlineWidth) >= 1) {
      const c = parse(st.outlineColor);
      if (c && c[3] > 0.02) lines.push({ side: 'Outline', c, w: parseFloat(st.outlineWidth), prop: 'outline', el, pseudo: null });
    }
    for (const ps of ['::before', '::after']) {
      const p = getComputedStyle(el, ps);
      if (p.content === 'none') continue;
      const pw = parseFloat(p.width) || r.width, ph = parseFloat(p.height) || r.height;
      const b = parse(p.backgroundColor);
      if (b && b[3] > 0.02 && Math.min(pw, ph) <= 4 && Math.max(pw, ph) >= 16) lines.push({ side: pw > ph ? 'Top' : 'Left', c: b, w: Math.min(pw, ph), prop: 'background', el, pseudo: ps, len: Math.max(pw, ph) });
      for (const side of ['Top', 'Left']) {
        const w = parseFloat(p[`border${side}Width`]), c = parse(p[`border${side}Color`]);
        if (w >= 1 && c && c[3] > 0.02 && p[`border${side}Style`] !== 'none') lines.push({ side, c, w, prop: 'border', el, pseudo: ps, len: side === 'Top' ? pw : ph });
      }
    }
    // 细长的有色元素本身就是线(活动标签顶线, 活动栏指示条等)
    const ownBg = parse(st.backgroundColor);
    if (ownBg && ownBg[3] > 0.02 && Math.min(r.width, r.height) <= 4 && Math.max(r.width, r.height) >= 16) {
      lines.push({ side: r.width > r.height ? 'Top' : 'Left', c: ownBg, w: Math.min(r.width, r.height), prop: 'background', el, pseudo: null, len: Math.max(r.width, r.height), self: true });
    }
    for (const ln of lines) {
      const horiz = ln.side === 'Top' || ln.side === 'Bottom' || ln.side === 'Outline';
      const len = ln.len || (horiz ? r.width : r.height);
      if (len < 8) continue;
      // 线外侧与内侧的底色
      let ox = cx, oy = cy, ix = cx, iy = cy;
      if (ln.side === 'Top' || ln.side === 'Outline') { oy = r.top - 3; iy = r.top + ln.w + 3; }
      if (ln.side === 'Bottom') { oy = r.bottom + 3; iy = r.bottom - ln.w - 3; }
      if (ln.side === 'Left') { ox = r.left - 3; ix = r.left + ln.w + 3; }
      if (ln.side === 'Right') { ox = r.right + 3; ix = r.right - ln.w - 3; }
      if (ln.self) { if (horiz) { oy = r.top - 3; iy = r.bottom + 3; } else { ox = r.left - 3; ix = r.right + 3; } }
      const out = bgAt(ox, oy, null).c, inn = ln.self ? bgAt(ix, iy, null).c : bgAt(ix, iy, el).c;
      const col = over(ln.c, out);
      const vis = Math.max(cr(col, out), cr(col, inn));
      const k = oklch(col);
      const focus = ln.prop === 'outline' || /focus|active-item-indicator|tab-border-top|active-border/.test(el.className);
      let level = null, kind = focus ? '焦点 / 指示线' : '边框 / 分隔线';
      if (focus && vis < 1.6) level = '看不清';
      else if (focus && vis < 3) level = '偏淡';
      else if (!focus && vis < 1.12 && ln.c[3] > 0.3) level = '偏淡';
      if (!level && len >= 150 && k.C >= 0.08 && vis >= 4.5) { level = '刺眼'; kind = '高饱和长线'; }
      else if (!level && k.C >= 0.12 && vis >= 6 && len >= 40) { level = '偏刺眼'; kind = '高饱和线'; }
      if (!level) continue;
      const rr = ln.side === 'Outline' ? r : {
        left: ln.side === 'Right' ? r.right - ln.w : r.left, top: ln.side === 'Bottom' ? r.bottom - ln.w : r.top,
        width: horiz ? Math.max(len, r.width) : ln.w, height: horiz ? ln.w : Math.max(len, r.height),
      };
      const actual = ln.pseudo ? getComputedStyle(el, ln.pseudo)[ln.prop === 'background' ? 'backgroundColor' : `border${ln.side}Color`]
        : ln.prop === 'outline' ? st.outlineColor : ln.prop === 'background' ? st.backgroundColor : st[`border${ln.side}Color`];
      add({
        kind, level, ratio: +vis.toFixed(2), fg: hex(col), bg: hex(out), fgRaw: rawHex(ln.c), opacity: 1,
        fgSrc: sourceOf(el, ln.prop, actual, ln.pseudo), bgSrc: { keys: [], how: 'none' },
        rect: rect({ left: rr.left, top: rr.top, width: Math.max(rr.width, 2), height: Math.max(rr.height, 2) }), ...lb, line: `${ln.pseudo || ''}${ln.prop}-${ln.side}`,
      });
    }

    // ---- 高亮底 / 大色块 / 徽标底 ----
    if (ownBg && ownBg[3] > 0.02 && Math.min(r.width, r.height) > 4) {
      const under = (() => {
        const stack = document.elementsFromPoint(cx, cy);
        const i = stack.findIndex((e) => e === el || e.contains(el));
        return compose(i < 0 ? [] : stack.slice(i + 1)).c;
      })();
      const col = over([...ownBg.slice(0, 3), ownBg[3] * opacityOf(el)], under);
      const vis = cr(col, under);
      const k = oklch(col);
      const area = r.width * r.height;
      const hl = /\b(selected|focused|findMatch|currentFindMatch|selectionHighlight|wordHighlight|rangeHighlight|selected-text|highlight)\b/.test(el.className);
      let level = null, kind = null;
      if (hl && vis < 1.04) { level = '看不清'; kind = '高亮底'; }
      else if (hl && vis < 1.1) { level = '偏淡'; kind = '高亮底'; }
      else if (area >= 1500 && ownBg[3] > 0.5 && k.C >= 0.1 && (dark ? k.L >= 0.62 : vis >= 5 && k.C >= 0.15)) { level = '刺眼'; kind = '大块高饱和底'; }
      else if (area < 1500 && k.C >= 0.15 && (dark ? k.L >= 0.75 : k.L <= 0.45) && vis >= 5) { level = '偏刺眼'; kind = '小块高饱和底(徽标 / 按钮)'; }
      if (level) add({
        kind, level, ratio: +vis.toFixed(2), fg: hex(col), bg: hex(under), fgRaw: rawHex(ownBg), opacity: +opacityOf(el).toFixed(2),
        fgSrc: sourceOf(el, 'background', st.backgroundColor), bgSrc: { keys: [], how: 'none' }, rect: rect(r), ...lb,
      });
    }
  }

  // 同一画面里同样的问题(种类, 颜色, 来源都相同)合并, 取面积最大的一处截图
  const sev = { 看不清: 0, 刺眼: 1, 偏淡: 2, 偏刺眼: 3 };
  const groups = new Map();
  for (const it of items) {
    const sig = [it.kind, it.level, it.fg, it.bg, it.fgSrc.keys[0] || '', it.bgSrc.keys[0] || ''].join('|');
    const g = groups.get(sig);
    if (!g) groups.set(sig, { ...it, sig, count: 1, texts: [it.text].filter(Boolean) });
    else {
      g.count++;
      if (it.text && g.texts.length < 5 && !g.texts.includes(it.text)) g.texts.push(it.text);
      if (it.rect.w * it.rect.h > g.rect.w * g.rect.h && it.rect.w * it.rect.h < 300000) Object.assign(g, { rect: it.rect, path: it.path, text: it.text });
    }
  }
  return { dark, base: hex(base), size: [W, H], items: [...groups.values()].sort((a, b) => sev[a.level] - sev[b.level] || a.ratio - b.ratio) };
}

export async function audit(page, { dir, name, log }) {
  const out = path.join(dir, 'audit');
  fs.mkdirSync(out, { recursive: true });
  const res = await page.evaluate(inspect);
  const items = res.items.slice(0, MAX_ITEMS);
  const [W, H] = res.size;
  for (const [i, it] of items.entries()) {
    const r = it.rect;
    // 太大的块只截中心一段, 保持局部图可读
    const cw = Math.min(r.w, 900), ch = Math.min(r.h, 360);
    const cx0 = r.x + (r.w - cw) / 2, cy0 = r.y + (r.h - ch) / 2;
    const clip = { x: Math.max(0, cx0 - PAD), y: Math.max(0, cy0 - PAD) };
    clip.width = Math.min(W, cx0 + cw + PAD) - clip.x;
    clip.height = Math.min(H, cy0 + ch + PAD) - clip.y;
    if (clip.width < 4 || clip.height < 4) continue;
    await page.evaluate((b) => {
      const d = document.createElement('div');
      d.id = '__audit_box';
      Object.assign(d.style, { position: 'fixed', left: `${b.x - 3}px`, top: `${b.y - 3}px`, width: `${b.w + 6}px`, height: `${b.h + 6}px`,
        outline: '2px dashed #FF2BD6', zIndex: 2147483647, pointerEvents: 'none' });
      document.body.appendChild(d);
    }, { x: cx0, y: cy0, w: cw, h: ch });
    it.crop = `${name}-${String(i).padStart(2, '0')}.png`;
    await page.screenshot({ path: path.join(out, it.crop), clip });
    await page.evaluate(() => document.getElementById('__audit_box')?.remove());
  }
  fs.writeFileSync(path.join(out, `${name}.json`), JSON.stringify({ ...res, items, dropped: Math.max(0, res.items.length - MAX_ITEMS) }, null, 1));
  log(`检查 ${name}: ${res.items.length} 类问题${res.items.length > MAX_ITEMS ? `(截图前 ${MAX_ITEMS})` : ''}`);
}
