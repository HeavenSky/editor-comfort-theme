// 门槛标定的普查钩子: 由 tools/shoot/shoot.mjs 在每张截图后调用(任务里写 "audit": "tools/lab/census-dom.mjs"), 不判对错, 把画面上全部
// 文字 / 图标 / 边框 / 指示线 / 高亮底 / 色块按角色记下: 自身颜色(字色, 线色或填充色)与它下面叠出的底色, WCAG 对比度, APCA Lc,
// 以及两种颜色各自的来源颜色键(供 tools/lab/threshold-lab.mjs 按 tools/lab/key-levels.mjs 的分层归组).
// 每个角色按对比度分层抽样截局部图(最低几处, 最高一处, 中间按分位), 问题位置加虚线框.
// 输出: <dir>/census/<name>.json 与 <dir>/census/<name>-<序号>.png; 每个主题的 a 场景另存 <主题>-vars.json(全部颜色键的实际取值, 含 VS Code 推导的默认值)
import fs from 'node:fs';
import path from 'node:path';

const PAD = 24;
const PER_ROLE = 7;

// 页面内执行: 只能用浏览器 API; 来源键查找与 tools/lab/audit-dom.mjs 的 sourceOf 同一套做法, 两边改动要同步
function collect() {
  const parse = (s) => {
    const m = s && s.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null;
  };
  const over = (top, under) => [0, 1, 2].map((i) => top[i] * top[3] + under[i] * (1 - top[3])).concat(1);
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  const wcag = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  // APCA-W3 0.0.98G-4g; 返回 |Lc|
  const apca = (txt, bg) => {
    const Y = (c) => 0.2126729 * (c[0] / 255) ** 2.4 + 0.7151522 * (c[1] / 255) ** 2.4 + 0.0721750 * (c[2] / 255) ** 2.4;
    const clamp = (y) => (y > 0.022 ? y : y + (0.022 - y) ** 1.414);
    const t = clamp(Y(txt)), b = clamp(Y(bg));
    if (Math.abs(b - t) < 0.0005) return 0;
    let out;
    if (b > t) { const s = (b ** 0.56 - t ** 0.57) * 1.14; out = s < 0.1 ? 0 : s - 0.027; }
    else { const s = (b ** 0.65 - t ** 0.62) * 1.14; out = s > -0.1 ? 0 : s + 0.027; }
    return Math.abs(out * 100);
  };
  const hex = (c) => '#' + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();
  const rawHex = (c) => hex(c) + (c[3] < 1 ? Math.round(c[3] * 255).toString(16).padStart(2, '0').toUpperCase() : '');
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
  const W = innerWidth, H = innerHeight;

  // ---- 来源键 ----
  const varVal = {};
  for (const sh of document.styleSheets) {
    let rules; try { rules = sh.cssRules; } catch { continue; }
    for (const r of rules) { if (!r.style) continue; for (let i = 0; i < r.style.length; i++) if (r.style[i].startsWith('--vscode-')) varVal[r.style[i]] = 1; }
  }
  for (let i = 0; i < wb.style.length; i++) if (wb.style[i].startsWith('--vscode-')) varVal[wb.style[i]] = 1;
  const byValue = {};
  for (const v of Object.keys(varVal)) { const k = norm(wst.getPropertyValue(v)); if (k) (byValue[k] ||= []).push(v); }
  const colorRules = [];
  const walk = (rules) => {
    for (const r of rules) {
      if (r.cssRules && !r.selectorText) { walk(r.cssRules); continue; }
      if (!r.selectorText || !r.style) continue;
      const props = {};
      for (let i = 0; i < r.style.length; i++) {
        const p = r.style[i];
        if (!/color|background|border|outline|shadow/.test(p)) continue;
        const vs = r.style.getPropertyValue(p).match(/--vscode-[\w-]+/g) || [];
        if (vs.length) props[p] = vs;
      }
      if (Object.keys(props).length) colorRules.push({ sel: r.selectorText, props });
    }
  };
  for (const sh of document.styleSheets) { try { walk(sh.cssRules); } catch {} }
  const keyOf = (v) => v.replace(/^--vscode-/, '').replace(/-/g, '.');
  const AREA = {
    sidebar: ['sideBar', 'list', 'tree', 'gitDecoration', 'scm', 'input', 'search'], auxiliarybar: ['sideBar', 'list'],
    panel: ['panel', 'problems', 'list', 'terminal', 'input', 'dropdown'], editor: ['editor', 'tab', 'breadcrumb', 'editorGroup', 'editorGutter', 'editorLineNumber'],
    activitybar: ['activityBar'], statusbar: ['statusBar'], titlebar: ['titleBar', 'commandCenter'],
  };
  const area = (el) => (el.closest('[id^="workbench.parts."]')?.id || '').replace('workbench.parts.', '');
  // 按值反查只留与属性类型相符的键: 字色只认前景类, 填充只认底色类, CSS 边框只认边框 / 线条类; 同色的别类键会把文字认成底色键
  const KIND_OK = { color: /foreground|Foreground\d?$|Color$|^foreground$|^terminal\.ansi/, background: /background|Background\d?$/, border: /border|Border|outline|Outline|stroke|Stroke|separator|sash/, outline: /border|Border|outline|Outline/ };
  const rank = (el, kind, keys) => {
    keys = keys.filter((k) => !KIND_OK[kind] || KIND_OK[kind].test(k));
    if (keys.length < 2) return keys;
    const pre = AREA[area(el)] || [];
    const suf = kind === 'color' ? /foreground$/i : kind === 'background' ? /background$/i : /border|outline/i;
    const score = (k) => (pre.some((p) => k.startsWith(p)) ? 2 : 0) + (suf.test(k) ? 1 : 0)
      - (/^(agent|chat|notebook|testing|debug|inlineChat|interactive|merge|diffEditor|minimap|walkThrough|welcome|extension|settings|keybinding|ports|profile|commentsView|gauge|simpleFind|radio|toolbar|editorHoverWidget|editorStickyScroll)/.test(k) ? 1 : 0);
    const best = Math.max(...keys.map(score));
    return keys.filter((k) => score(k) === best);
  };
  const sourceOf = (el, kind, actual, pseudo) => {
    if (!el) return { keys: [], how: 'none' };
    const want = norm(actual);
    const hit = new Set();
    const st = getComputedStyle(el);
    for (const r of colorRules) {
      const sels = r.sel.split(',').map((x) => x.trim()).filter((x) => (pseudo ? x.includes(pseudo) : !/::?(before|after)/.test(x)));
      if (!sels.length) continue;
      if (!sels.some((x) => { try { return el.matches(x.replace(/::?(before|after)/g, '').replace(/:(hover|active)/g, '') || '*'); } catch { return false; } })) continue;
      for (const [p, vs] of Object.entries(r.props)) {
        if (kind === 'color' ? p !== 'color' : !p.startsWith(kind)) continue;
        for (const v of vs) if (norm(st.getPropertyValue(v)) === want) hit.add(v);
      }
    }
    for (const v of (el.getAttribute('style') || '').match(/--vscode-[\w-]+/g) || []) if (norm(st.getPropertyValue(v)) === want) hit.add(v);
    let keys = [...hit].map(keyOf), how = 'rule';
    if (!keys.length) { keys = rank(el, kind, (byValue[want] || []).map(keyOf)); how = keys.length ? 'value' : 'none'; }
    return { keys: [...new Set(keys)].slice(0, 6), how };
  };

  // ---- 叠色 ----
  const opacityOf = (el) => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= +getComputedStyle(e).opacity; return o; };
  // 底色与最上层出底色的元素(来源键用)
  const compose = (list) => {
    let c = base, src = null;
    for (const e of [...list].reverse()) { const b = parse(getComputedStyle(e).backgroundColor); if (b && b[3] > 0.01) { c = over(b, c); src = e; } }
    return { c, src };
  };
  const bgAt = (x, y, el) => {
    const stack = document.elementsFromPoint(Math.min(W - 1, Math.max(0, x)), Math.min(H - 1, Math.max(0, y)));
    const i = el ? stack.findIndex((e) => e === el || e.contains(el)) : 0;
    if (i >= 0) return compose(stack.slice(i));
    const chain = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) chain.push(e);
    return compose(chain);
  };
  const visible = (el, r) => {
    if (r.width < 2 || r.height < 2 || r.right < 0 || r.bottom < 0 || r.left > W || r.top > H) return false;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none') return false;
    const top = document.elementFromPoint(Math.min(W - 1, Math.max(0, r.left + r.width / 2)), Math.min(H - 1, Math.max(0, r.top + r.height / 2)));
    return !!top && (el.contains(top) || top.contains(el));
  };
  const pathOf = (el) => `${area(el)} ${el.tagName.toLowerCase()}${typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : ''}`;
  const textRole = (el) => {
    if (el.closest('.view-lines')) return '代码';
    if (el.closest('.line-numbers.active-line-number')) return '当前行号';
    if (el.closest('.line-numbers')) return '行号';
    if (el.closest('.tab.active')) return '活动标签';
    if (el.closest('.disabled, [aria-disabled="true"]')) return '禁用';
    if (el.closest('.badge, .monaco-count-badge, .badge-content')) return '徽标文字';
    if (el.closest('.monaco-button, .monaco-text-button')) return '按钮文字';
    if (el.closest('.tab:not(.active)')) return '非活动标签';
    if (el.closest('.label-description, .description, .monaco-icon-description-container, .breadcrumbs-control, .marker-line, .monaco-tl-twistie, .count, .monaco-icon-suffix-container, .details, .label-suffix')) return '次要文字';
    if (el.closest('.monaco-list-row.selected, .monaco-list-row.focused')) return '选中行文字';
    if (el.closest('.part.statusbar')) return '状态栏文字';
    return '主要文字';
  };

  // 先按 角色 + 自身色 + 底色 去重, 每组只给代表元素查来源键
  const uniq = new Map();
  const push = (role, self, under, q, src, extra = {}) => {
    const k = `${role}|${hex(self)}|${hex(under)}`;
    const g = uniq.get(k);
    const rect = { x: Math.round(q.left), y: Math.round(q.top), w: Math.round(q.width), h: Math.round(q.height) };
    if (g) { g.count++; if (extra.text && g.texts.length < 4 && !g.texts.includes(extra.text)) g.texts.push(extra.text); return; }
    uniq.set(k, { role, fg: hex(self), bg: hex(under), wcag: +wcag(self, under).toFixed(2), apca: +apca(self, under).toFixed(1), rect, count: 1,
      texts: extra.text ? [extra.text] : [], size: extra.size, weight: extra.weight, line: extra.line, thick: extra.thick, area: extra.area, src });
  };
  for (const el of wb.querySelectorAll('*')) {
    // 颜色选择器色块画的是文件里写的颜色值, 不是主题颜色
    if (el.closest('.minimap, .xterm, .monaco-aria-container, .colorpicker-color-decoration')) continue;
    const r = el.getBoundingClientRect();
    // 空白符(普查打开 renderWhitespace 后显示)按行画成 SVG 小圆点, 颜色在 fill 属性里, 取 editorWhitespace.foreground; 它压在文字下面, 不走可见性判断
    if (el.tagName === 'svg' && el.closest('.view-overlays') && el.getAttribute('fill') && el.querySelector('path')) {
      const fill = parse(el.getAttribute('fill') || '') || hexRgb(el.getAttribute('fill'));
      if (fill && r.width > 2 && r.bottom > 0 && r.top < H && r.left < W) {
        const { c: bg, src: bgEl } = bgAt(r.left + Math.min(r.width / 2, 60), r.top + r.height / 2, el);
        push('空白符', over([...fill.slice(0, 3), fill[3] * opacityOf(el)], bg), bg, r, { el, fixed: ['editorWhitespace.foreground'], bgEl });
      }
      continue;
    }
    if (!visible(el, r)) continue;
    const st = getComputedStyle(el);
    const op = opacityOf(el);
    const role0 = textRole(el);
    // 文字 / 图标
    const txt = [...el.childNodes].filter((n) => n.nodeType === 3 && n.textContent.trim());
    const icon = /\bcodicon\b/.test(el.className) && getComputedStyle(el, '::before').content !== 'none';
    const fg0 = parse(st.color);
    if ((txt.length || icon) && fg0 && fg0[3] * op > 0.05) {
      let q = r;
      if (txt.length) { const rg = document.createRange(); rg.selectNodeContents(txt[0]); const b = rg.getBoundingClientRect(); if (b.width > 1) q = b; }
      const { c: bg, src: bgEl } = bgAt(q.left + q.width / 2, q.top + q.height / 2, el);
      const fg = over([...fg0.slice(0, 3), fg0[3] * op], bg);
      const role = icon ? (el.closest('.disabled') ? '禁用' : area(el) === 'activitybar' ? (el.closest('.action-item.checked, .action-item.active') ? '活动栏选中图标' : '活动栏图标') : '图标') : role0;
      push(role, fg, bg, q, { el, kind: 'color', actual: st.color, bgEl },
        { text: txt.length ? txt[0].textContent.trim().slice(0, 40) : el.getAttribute('aria-label')?.slice(0, 40) || '', size: parseFloat(st.fontSize), weight: +st.fontWeight || 400 });
    }
    // 边框, 焦点描边, 细长色条
    const lines = [];
    for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
      const w = parseFloat(st[`border${side}Width`]), c = parse(st[`border${side}Color`]);
      if (w >= 1 && c && c[3] > 0.02 && st[`border${side}Style`] !== 'none') lines.push({ side, c, w, kind: 'border', actual: st[`border${side}Color`] });
    }
    if (st.outlineStyle !== 'none' && parseFloat(st.outlineWidth) >= 1) { const c = parse(st.outlineColor); if (c && c[3] > 0.02) lines.push({ side: 'Outline', c, w: parseFloat(st.outlineWidth), focus: true, kind: 'outline', actual: st.outlineColor }); }
    for (const ps of ['::before', '::after']) {
      const p = getComputedStyle(el, ps);
      if (p.content === 'none') continue;
      const pw = parseFloat(p.width) || r.width, ph = parseFloat(p.height) || r.height, b = parse(p.backgroundColor);
      if (b && b[3] > 0.02 && Math.min(pw, ph) <= 4 && Math.max(pw, ph) >= 16) lines.push({ side: pw > ph ? 'Top' : 'Left', c: b, w: Math.min(pw, ph), kind: 'background', actual: p.backgroundColor, pseudo: ps });
      for (const side of ['Top', 'Left']) {
        const w = parseFloat(p[`border${side}Width`]), c = parse(p[`border${side}Color`]);
        if (w >= 1 && c && c[3] > 0.02 && p[`border${side}Style`] !== 'none') lines.push({ side, c, w, kind: 'border', actual: p[`border${side}Color`], pseudo: ps });
      }
    }
    const ownBg = parse(st.backgroundColor);
    const thin = Math.min(r.width, r.height) <= 4 && Math.max(r.width, r.height) >= 16;
    if (ownBg && ownBg[3] > 0.02 && thin) lines.push({ side: r.width > r.height ? 'Self-h' : 'Self-v', c: ownBg, w: Math.min(r.width, r.height), kind: 'background', actual: st.backgroundColor });
    for (const ln of lines) {
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      let ox = cx, oy = cy;
      if (ln.side === 'Top' || ln.side === 'Outline' || ln.side === 'Self-h') oy = r.top - 3;
      if (ln.side === 'Bottom') oy = r.bottom + 3;
      if (ln.side === 'Left' || ln.side === 'Self-v') ox = r.left - 3;
      if (ln.side === 'Right') ox = r.right + 3;
      const { c: out, src: bgEl } = bgAt(ox, oy, null);
      const col = over([...ln.c.slice(0, 3), ln.c[3] * op], out);
      const focus = ln.focus || /focus|active-item-indicator|tab-border-top|active-border|selected/.test(el.className + ' ' + (el.parentElement?.className || ''));
      // 记那条线本身的位置与粗细(局部图只框这条线, 不框整个元素); 伪元素的位置取不到, 按所在元素的同侧边近似
      const t = Math.max(1, Math.round(ln.w || 1));
      const lr = ln.side === 'Top' ? { left: r.left, top: r.top, width: r.width, height: t } : ln.side === 'Bottom' ? { left: r.left, top: r.bottom - t, width: r.width, height: t }
        : ln.side === 'Left' ? { left: r.left, top: r.top, width: t, height: r.height } : ln.side === 'Right' ? { left: r.right - t, top: r.top, width: t, height: r.height } : r;
      push(focus ? '焦点 / 指示线' : '边框 / 分隔线', col, out, lr, { el, kind: ln.kind, actual: ln.actual, pseudo: ln.pseudo, bgEl }, { line: ln.side, thick: t });
    }
    // 高亮底与色块: 和它下面的底色比
    if (ownBg && ownBg[3] > 0.02 && !thin && r.width * r.height >= 60) {
      const stack = document.elementsFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      const i = stack.findIndex((e) => e === el || e.contains(el));
      const { c: under, src: bgEl } = compose(i < 0 ? [] : stack.slice(i + 1));
      const col = over([...ownBg.slice(0, 3), ownBg[3] * op], under);
      if (hex(col) === hex(under)) continue;
      const hl = /\b(selected|focused|findMatch|currentFindMatch|selectionHighlight|wordHighlight|rangeHighlight|selected-text|current-line|highlight)\b/.test(el.className);
      const badge = !!el.closest('.badge, .monaco-count-badge, .badge-content, .monaco-button');
      push(hl ? '高亮底' : badge ? '徽标 / 按钮底' : '色块底', col, under, r, { el, kind: 'background', actual: st.backgroundColor, bgEl }, { area: Math.round(r.width * r.height) });
    }
  }
  const items = [];
  for (const it of uniq.values()) {
    const s = it.src;
    // 编辑区代码的字色来自语法规则, 不是界面颜色键
    const self = s.fixed ? { keys: s.fixed, how: 'fixed' } : it.role === '代码' ? { keys: [], how: 'token' } : sourceOf(s.el, s.kind, s.actual, s.pseudo);
    const under = s.bgEl ? sourceOf(s.bgEl, 'background', getComputedStyle(s.bgEl).backgroundColor) : { keys: ['editor.background'], how: 'base' };
    delete it.src;
    items.push({ ...it, path: pathOf(s.el), selfKeys: self.keys, selfHow: self.how, underKeys: under.keys, underHow: under.how });
  }
  return { dark: lum(base) < 0.2, base: hex(base), size: [W, H], items };
}

export async function audit(page, { dir, name, log }) {
  const out = path.join(dir, 'census');
  fs.mkdirSync(out, { recursive: true });
  const res = await page.evaluate(collect);
  const items = res.items;
  // 分层抽样截图: 每个角色最低 3 处, 最高 1 处, 中间按分位取
  const byRole = {};
  for (const it of items) (byRole[it.role] ||= []).push(it);
  const pick = new Set();
  for (const list of Object.values(byRole)) {
    list.sort((a, b) => a.wcag - b.wcag);
    const idx = new Set([0, 1, 2, list.length - 1]);
    for (let q = 1; q < PER_ROLE - 3; q++) idx.add(Math.floor((list.length * q) / (PER_ROLE - 3)));
    for (const i of idx) if (list[i]) pick.add(list[i]);
  }
  const [W, H] = res.size;
  let n = 0;
  for (const it of pick) {
    const r = it.rect;
    const cw = Math.min(r.w, 700), ch = Math.min(r.h, 240);
    const x0 = r.x + (r.w - cw) / 2, y0 = r.y + (r.h - ch) / 2;
    const clip = { x: Math.max(0, x0 - PAD), y: Math.max(0, y0 - PAD) };
    clip.width = Math.min(W, x0 + cw + PAD) - clip.x;
    clip.height = Math.min(H, y0 + ch + PAD) - clip.y;
    if (clip.width < 4 || clip.height < 4) continue;
    await page.evaluate((b) => {
      const d = document.createElement('div');
      d.id = '__census_box';
      Object.assign(d.style, { position: 'fixed', left: `${b.x - 3}px`, top: `${b.y - 3}px`, width: `${b.w + 6}px`, height: `${b.h + 6}px`,
        outline: '2px dashed #FF2BD6', zIndex: 2147483647, pointerEvents: 'none' });
      document.body.appendChild(d);
    }, { x: x0, y: y0, w: cw, h: ch });
    it.crop = `${name}-${String(n++).padStart(3, '0')}.png`;
    await page.screenshot({ path: path.join(out, it.crop), clip });
    await page.evaluate(() => document.getElementById('__census_box')?.remove());
  }
  fs.writeFileSync(path.join(out, `${name}.json`), JSON.stringify({ dark: res.dark, base: res.base, size: res.size, items }));
  if (name.endsWith('-a')) {
    const vars = await page.evaluate(() => {
      const wb = document.querySelector('.monaco-workbench'), st = getComputedStyle(wb), names = new Set(), out = {};
      for (const sh of document.styleSheets) { try { for (const r of sh.cssRules) if (r.style) for (let i = 0; i < r.style.length; i++) if (r.style[i].startsWith('--vscode-')) names.add(r.style[i]); } catch {} }
      for (let i = 0; i < wb.style.length; i++) if (wb.style[i].startsWith('--vscode-')) names.add(wb.style[i]);
      for (const n of names) { const v = st.getPropertyValue(n).trim(); if (/^#[0-9a-f]{3,8}$|^rgba?\(/i.test(v)) out[n.slice(9).replace(/-/g, '.')] = v; }
      return out;
    });
    fs.writeFileSync(path.join(out, `${name.slice(0, -2)}-vars.json`), JSON.stringify(vars));
  }
  log(`普查 ${name}: ${items.length} 组色对, 截图 ${n} 张`);
}
