# 门禁打分: 范围(终端 / 编辑区 / 界面) x 清晰维度(读得清, 分得开); metrics.py 与 similar.py 共用,
# 顶部的界面常量也是 gen_vscode.py 的调色口径.
#
# 每个子指标给出 理想区间 与 限值区间: 落在理想区间得 100, 到限值线性降到 60, 越过限值继续线性降到 0 并判失败.
# 一格(维度 x 范围)的得分为其子指标得分的平均; 通过 = 没有子指标越过限值. 指标取不到(例如 .terminal 没有编辑区)时跳过.
# 鲜艳柔和 / 防疲劳 / 护眼 / 防蓝光 四个维度是 v0.0.3 舒适度重调时期的口径, 与"保留原主题亮度与饱和度"相反, 已删除.
import math

from colorlib import Rgb, blend, cr, de2000, h, lum, oklch

# 输入框 / 下拉框等控件里输入的字(计入 小块上的字)
CONTROL_TEXT_PAIRS = [('input.foreground', 'input.background'), ('dropdown.foreground', 'dropdown.background'),
                      ('settings.textInputForeground', 'settings.textInputBackground'),
                      ('settings.dropdownForeground', 'settings.dropdownBackground')]
# 焦点 / 选项激活描边: 指示器要看得见
FOCUS_KEYS = ['focusBorder', 'inputOption.activeBorder']
# 画在代码文字下面的高亮底色: 压在上面的正文要好读
HIGHLIGHT_KEYS = [
    'editor.selectionBackground', 'editor.findMatchBackground', 'editor.findMatchHighlightBackground',
    'editor.hoverHighlightBackground', 'editor.wordHighlightBackground', 'editor.wordHighlightStrongBackground',
    'editor.selectionHighlightBackground', 'peekViewEditor.matchHighlightBackground', 'peekViewResult.matchHighlightBackground',
    'editor.rangeHighlightBackground', 'editorBracketMatch.background', 'mergeEditor.changeBase.word.background',
    'diffEditor.insertedTextBackground', 'diffEditor.removedTextBackground',
]
HIGHLIGHT_TEXT_MIN = 3.5
# 徽标(活动栏角标, 计数等): 上面的字要可读(计入 小块上的字)
BADGE_PAIRS = [
    ('activityBarBadge.background', 'activityBarBadge.foreground'), ('badge.background', 'badge.foreground'),
    ('activityErrorBadge.background', 'activityErrorBadge.foreground'),
    ('activityWarningBadge.background', 'activityWarningBadge.foreground'), ('agentsBadge.background', 'agentsBadge.foreground'),
    ('agentsUnreadBadge.background', 'agentsUnreadBadge.foreground'), ('panelTitleBadge.background', 'panelTitleBadge.foreground'),
    ('profileBadge.background', 'profileBadge.foreground'), ('extensionBadge.remoteBackground', 'extensionBadge.remoteForeground'),
    ('testing.coverCountBadgeBackground', 'testing.coverCountBadgeForeground'),
    ('testing.message.error.badgeBackground', 'testing.message.error.badgeForeground'),
]
# 选中文字的底: 编辑区选区(editor.selectionBackground, 叠在编辑区底上)与输入框里选中文字的底(selection.background, 叠在输入框底上,
# 如搜索框, 筛选框). 要看得出选中了, 压在上面的字仍可读; selection.background 不定义时由系统高亮色决定, 一律要求定义
SELECTION_VISIBLE = (1.3, 1.15)
INPUT_SELECTION_TEXT = (4.0, 3.5)


def input_selection(colors: dict, bg: Rgb) -> tuple[Rgb, Rgb | None, Rgb]:
    """(输入框底, 叠上 selection.background 后的选区色(未定义时为 None), 输入框文字色)."""
    inp = _parse(colors['input.background'], bg) if 'input.background' in colors else bg
    text = colors.get('input.foreground') or colors.get('foreground') or colors.get('editor.foreground')
    sel = _parse(colors['selection.background'], inp) if 'selection.background' in colors else None
    return inp, sel, _parse(text, inp) if text else inp


# 彩度低于它的语法色视为中性(与正文同色的标点, 运算符等), 不计入亮度跨度
NEUTRAL_CHROMA = 0.035


# ======== 门禁: 范围 x 清晰维度 ========
# 范围: 终端 / 编辑区 / 界面(其余位置: 侧栏, 标签栏, 状态栏, 面板, 弹窗, 徽标, 控件). 综合分按 SCOPE_WEIGHTS 加权.
# 每格(维度 x 范围)= 子指标得分平均; 范围分 = 各维度平均; 维度分 = 各范围按 SCOPE_WEIGHTS 加权; 任一子指标越限即不通过.
SCOPES = ['term', 'editor', 'ui']
SCOPE_NAMES = dict(term='终端', editor='编辑区', ui='界面')
SCOPE_WEIGHTS = dict(term=2, editor=2, ui=1)
DIMS = ['clear']
DIM_NAMES = dict(clear='清晰')

TERM_COLORS = ['Red', 'Green', 'Yellow', 'Blue', 'Magenta', 'Cyan']
# 各槽位的 OKLCH 色相范围(度, 允许跨 0): 拦串色(如蓝槽是橙色, 黄槽是柠檬绿); 相邻槽有重叠, 容纳官方色板的刻意设计
# (Solarized 亮紫用 violet 279°, Dracula 亮蓝偏紫 308°); Night Owl 的黄 122° 已是黄绿, 不收
TERM_HUES = dict(Red=(340, 55), Yellow=(55, 115), Green=(110, 170), Cyan=(160, 240), Blue=(225, 312), Magenta=(270, 25))
# 主要语法角色(pool.ROLES): 两两要分得开, 也都不能发灰
MAIN_ROLES = ['keyword', 'string', 'function', 'type', 'number']
# 界面状态色: 组内两两要分得开(错误 / 警告 / 信息; git 修改 / 新增 / 删除)
STATUS_GROUPS = [['editorError.foreground', 'editorWarning.foreground', 'editorInfo.foreground'],
                 ['gitDecoration.modifiedResourceForeground', 'gitDecoration.untrackedResourceForeground',
                  'gitDecoration.deletedResourceForeground']]


def specs(dark: bool) -> dict:
    """(理想下限, 理想上限, 限值下限, 限值上限); None 表示该侧不设限. 返回 {维度: {范围: {子指标: spec}}}; 角色色差原主题多在 12 以上."""
    zero = (None, 0, None, 0)
    return dict(
        clear=dict(
            # 彩字: 浅底彩字 4.5 偏淡, 浅色主题理想下限取 5.0
            term=dict(text=(7.0, None, 6.0, None), accent=(4.5 if dark else 5.0, None, 4.0, None), bright=(5.5, None, 4.5, None),
                      badge=(5.0, None, 4.0, None), gray=(3.4, None, 3.0, None), distinct=(20, None, 12, None), hue_slot=zero,
                      # 选区(划选文字的底): 与终端底的对比度要看得出, 程序自己铺的浅色块(如 Codex 输入区)上也不消失;
                      # 失焦选区(VS Code 默认为选区的一半透明度)稍弱; 压在选区上的正文仍要可读
                      selection=(1.3, None, 1.2, None), inactive_selection=(1.15, None, 1.08, None),
                      on_selection=(4.5, None, 3.5, None)),
            editor=dict(text=(7.0 if dark else 7.5, None, 6.0, None), syntax=(5.0, None, 4.5, None), comment=(3.4, None, 3.0, None),
                        line_no=(2.0, None, 1.8, None), roles=(10, None, 5, None), on_highlight=(4.5, None, 3.5, None),
                        selection_visible=(SELECTION_VISIBLE[0], None, SELECTION_VISIBLE[1], None)),
            ui=dict(ui_text=(4.5, None, 4.0, None), small_text=(4.5, None, 3.5, None), focus=(3.0, None, 2.5, None),
                    status=(15, None, 8, None), input_selection=(SELECTION_VISIBLE[0], None, SELECTION_VISIBLE[1], None),
                    input_selection_text=(INPUT_SELECTION_TEXT[0], None, INPUT_SELECTION_TEXT[1], None)))
    )


def term_spec(dark: bool) -> dict:
    """终端范围的子指标表 {子指标: spec}: 终端色(.terminal, VS Code 的 terminal.*, Claude Code 主题)生成时只按它取目标,
    不借用编辑区 / 界面的口径."""
    sp = specs(dark)
    return {k: v for dim in DIMS for k, v in sp[dim]['term'].items()}


NAMES = dict(text='正文', accent='彩字', bright='亮色', badge='徽标字', gray='90m', distinct='最近色差', hue_slot='串色',
             selection='选区', inactive_selection='失焦选区', on_selection='选区上的字',
             selection_visible='编辑区选区', input_selection='输入框选区', input_selection_text='输入框选中的字',
             syntax='语法下限', comment='注释', line_no='行号', roles='角色色差', on_highlight='高亮上的字',
             ui_text='界面文字', small_text='小块上的字', focus='焦点描边', status='状态色差')



def _score(v: float, spec: tuple) -> tuple[float, bool]:
    ilo, ihi, llo, lhi = spec
    if (ilo is None or v >= ilo) and (ihi is None or v <= ihi):
        return 100.0, True
    if ihi is not None and v > ihi:
        edge, lim = ihi, lhi
    else:
        edge, lim = ilo, llo
    span = abs(lim - edge)
    if span == 0:
        return (0.0, False)
    d = abs(v - edge) / span
    return (max(0.0, 100 - 40 * d) if d <= 1 else max(0.0, 60 - 60 * (d - 1))), d <= 1


def _rate(values: dict, specs: dict) -> dict:
    subs, why = {}, []
    for k, spec in specs.items():
        v = values.get(k)
        if v is None:
            continue
        s, ok = _score(v, spec)
        subs[k] = (v, s)
        if not ok:
            lim = spec[3] if spec[3] is not None and v > spec[3] else spec[2]
            why.append(f"{NAMES[k]} {v:.3g} 越过限值 {lim}")
    score = round(sum(s for _, s in subs.values()) / len(subs)) if subs else None
    return dict(score=score, ok=not why, why=why, subs=subs)


def _parse(v: str, under: Rgb) -> Rgb:
    v = v.lstrip('#')
    if len(v) in (3, 4):
        v = ''.join(ch * 2 for ch in v)
    c = h(v[:6])
    return blend(c, under, int(v[6:8], 16) / 255) if len(v) == 8 else c


def _in_hue(deg: float, rng: tuple) -> bool:
    lo, hi = rng
    return lo <= deg <= hi if lo <= hi else deg >= lo or deg <= hi


def _deg(c: Rgb) -> float:
    return math.degrees(oklch(c)[2]) % 360


def _opaque(colors: dict, keys, bg: Rgb) -> list[Rgb]:
    return [_parse(colors[k], bg) for k in keys if k in colors]


def _min_de(cs: list[Rgb]) -> float | None:
    pairs = [de2000(a, b) for i, a in enumerate(cs) for b in cs[i + 1:]]
    return min(pairs) if pairs else None


def term_values(pal: list[Rgb], bg: Rgb, fg: Rgb, sel: Rgb | None = None, sel_inactive: Rgb | None = None) -> dict:
    """终端范围: pal 为 16 色(Black, Red, ..., White, BrightBlack, ...), bg / fg 为终端底色与正文,
    sel / sel_inactive 为叠到终端底上的选区 / 失焦选区(取不到时不计)."""
    normal, bright = pal[1:7], pal[9:15]
    colored = normal + bright
    names = TERM_COLORS + TERM_COLORS
    text = cr(fg, bg)
    crs = [cr(c, bg) for c in normal]
    return dict(
        clear=dict(text=text, accent=min(crs), bright=min(cr(c, bg) for c in bright),
                   badge=min(max(cr(pal[0], c), cr(pal[15], c), cr(pal[7], c)) for c in colored),
                   gray=cr(pal[8], bg), distinct=_min_de(normal),
                   hue_slot=sum(not _in_hue(_deg(c), TERM_HUES[n]) for n, c in zip(names, colored)),
                   selection=cr(sel, bg) if sel else None, inactive_selection=cr(sel_inactive, bg) if sel_inactive else None,
                   on_selection=cr(fg, sel) if sel else None),
    )


def editor_values(m: dict) -> dict:
    import pool
    bg, fg, colors, text = m['bg'], m['fg'], m['colors'], m['text']
    syn = m.get('syn_colors') or []
    fghex = '#%02X%02X%02X' % tuple(round(v * 255) for v in fg)
    roles = [pool._rgb(pool.role_value(m.get('rules') or [], r, fghex)) for r in MAIN_ROLES]
    roles = [_parse('#%02X%02X%02X' % tuple(round(v * 255) for v in c), bg) for c in roles if c]
    croles = [c for c in roles if oklch(c)[1] > NEUTRAL_CHROMA]
    under = _opaque(colors, HIGHLIGHT_KEYS, bg)
    comment = m.get('comment_main') or m.get('comment')
    return dict(
        clear=dict(text=text, syntax=min(cr(c, bg) for c in syn) if syn else None, comment=comment, line_no=m.get('line_no'),
                   roles=_min_de(croles), on_highlight=min((cr(fg, u) for u in under), default=None),
                   selection_visible=cr(_parse(colors['editor.selectionBackground'], bg), bg) if 'editor.selectionBackground' in colors else 1.0),
    )


def ui_values(m: dict) -> dict:
    bg, colors = m['bg'], m['colors']
    small = []
    for bk, fk in BADGE_PAIRS + [('button.background', 'button.foreground')]:
        if bk in colors and fk in colors:
            u = _parse(colors[bk], bg)
            small.append(cr(_parse(colors[fk], u), u))
    for fk, bk in CONTROL_TEXT_PAIRS:
        if fk in colors:
            u = _parse(colors[bk], bg) if bk in colors else bg
            small.append(cr(_parse(colors[fk], u), u))
    status = [_min_de(_opaque(colors, g, bg)) for g in STATUS_GROUPS]
    status = [x for x in status if x is not None]
    inp, isel, itext = input_selection(colors, bg)
    return dict(
        clear=dict(ui_text=m.get('ui'), small_text=min(small, default=None),
                   focus=min((cr(c, bg) for c in _opaque(colors, FOCUS_KEYS, bg)), default=None), status=min(status, default=None),
                   # 未定义 selection.background 按看不见计(由系统高亮色决定, 不可控)
                   input_selection=cr(isel, inp) if isel else 1.0, input_selection_text=cr(itext, isel) if isel else None),
    )


def _avg(items: list[tuple[float, float]]) -> float | None:
    w = sum(x for x, _ in items)
    return round(sum(x * s for x, s in items) / w) if w else None


def rate(m: dict) -> dict:
    """m 为 metrics.from_vscode / from_terminal 的结果. 返回
    cells {(维度, 范围): {score, ok, why, subs}}, scope {范围: {score, ok}}, dim {维度: {score, ok}}, overall {score, ok}, diag."""
    sp = specs(lum(m['bg']) < 0.2)
    values = {}
    if m.get('pal'):
        values['term'] = term_values(m['pal'], m['term_bg'], m['term_fg'], m.get('term_sel'), m.get('term_sel_inactive'))
    if m.get('colors') is not None:
        values['editor'] = editor_values(m)
        values['ui'] = ui_values(m)
    cells = {}
    for scope, vals in values.items():
        for dim in DIMS:
            r = _rate({k: v for k, v in vals[dim].items() if k in sp[dim][scope]}, sp[dim][scope])
            if r['score'] is not None:
                cells[(dim, scope)] = r
    ok = lambda rs: all(r['ok'] for r in rs)
    scope = {s: dict(score=_avg([(1, r['score']) for (d, s2), r in cells.items() if s2 == s]),
                     ok=ok([r for (d, s2), r in cells.items() if s2 == s])) for s in SCOPES if s in values}
    dim = {d: dict(score=_avg([(SCOPE_WEIGHTS[s], r['score']) for (d2, s), r in cells.items() if d2 == d]),
                   ok=ok([r for (d2, s), r in cells.items() if d2 == d])) for d in DIMS}
    overall = dict(score=_avg([(SCOPE_WEIGHTS[s], r['score']) for s, r in scope.items()]), ok=ok(cells.values()))
    # 诊断(不计分): 彩色语法色里彩度相同(±0.004)或对比度相同(±1.5%)的最大占比, 过高说明被同一个边界压平了
    diag = {}
    syn = [c for c in (m.get('syn_colors') or []) if oklch(c)[1] > NEUTRAL_CHROMA]
    if len(syn) >= 4:
        uniq = list(set(syn))
        share = lambda f, tol: max(sum(abs(f(a) - f(b)) <= tol(f(a)) for b in uniq) for a in uniq) / len(uniq)
        diag['same_chroma'] = share(lambda c: oklch(c)[1], lambda v: 0.004)
        diag['same_cr'] = share(lambda c: cr(c, m['bg']), lambda v: v * 0.015)
    return dict(cells=cells, scope=scope, dim=dim, overall=overall, diag=diag)
