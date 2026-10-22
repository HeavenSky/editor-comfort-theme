# 全部主题的定义, 是 VS Code 主题与 Terminal.app 主题的唯一数据来源.
#
# 每套主题都按补全段的中间主题 assets/full-theme/<name>-full.json(complete.py)适配: 底色, 正文, 光标, 选区与 16 色终端取自它,
# 再经 tools/gen/steps.py 登记的调色步骤调整; 步骤全关时这些值与 full 相同. Terminal 主题只用 bg / fg / bold / cursor / sel / ansi;
# VS Code 主题另用 sel / sel_inactive 作终端选区(term_selection 重算时才写回).
# 命名: <name>-dark / <name>-light(与 assets/source/ 的原主题同名), 显示名 C <Name> Dark / Light.
import json, os

from colorlib import unwhite, blend, cr, fit, h, hx, oklch, sat, with_sat
from comfort import TERM_COLORS, term_spec
from steps import on

SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'source')

ANSI = ['Black', 'Red', 'Green', 'Yellow', 'Blue', 'Magenta', 'Cyan', 'White']


def _ansi(normal: dict, bright: dict, grays: dict) -> dict:
    return {**normal, **{'Bright' + k: v for k, v in bright.items()}, **grays}




# 注释对比度: 'auto' 表示随正文联动(正文 / 1.85, 限制在 3.4~4.2, 见 gen_vscode.py), 偏低提升, 偏高压低
COMMENT_CR = 'auto'
# 深色主题语法色对比度上限 = 正文对比度 x SYNTAX_MAX: 彩色可以比正文略亮一点, 天生明亮的黄 / 青 / 绿不必压暗变灰
SYNTAX_MAX = 1.05
# 浅色主题语法色对比度上限 = 正文 x LIGHT_SYNTAX_MAX: 浅底上彩字比正文略深不刺眼; 区间太窄会把原主题的明暗层次挤到一起
LIGHT_SYNTAX_MAX = 1.12
# 可读下限(WCAG AA 4.5): 正文, 语法色, 终端彩色低于它才提; 不再按门禁理想值(正文 7 / 8, 语法 5.0, 终端亮色 6.5)提
LEGIBLE = 4.5
SYNTAX_MIN = LEGIBLE
# 对比度目标的余量(防 hex 取整)
TERM_MARGIN = 0.05


# 选区对比度目标在门禁 选区 / 失焦选区 理想下限上留的余量: 程序自己铺的浅色块(如 Codex 输入区)比终端底再近一档, 留足才看得出
TERM_SEL_MARGIN, TERM_SEL_INACTIVE_MARGIN = 0.1, 0.05


def term_selection(bg, fg, blue, target: float, dark: bool):
    """终端选区: 终端蓝按比例混进底色, 推到与底对比度 >= target; 压在上面的正文不低于 选区上的字 的理想下限(达不到时停在能保住正文的最强一档).
    正文本身只比理想下限高一点时(如 Sunlit 4.5~4.75)选区稍一显出来字就不够理想下限, 会停在底色上等于没有选区;
    这时正文改按 选区上的字 的限值(3.5, 同编辑区 高亮上的字)求色."""
    ts = term_spec(dark)
    for on_min in (ts['on_selection'][0] + TERM_MARGIN, ts['on_selection'][2] + TERM_MARGIN):
        best = bg
        for i in range(1, 201):
            c = blend(blue, bg, i / 200)
            if cr(fg, c) < on_min:
                break
            best = c
            if cr(c, bg) >= target:
                break
        if cr(best, bg) >= target:
            break
    return best


def term_accent_min(dark: bool) -> float:
    """终端彩色(普通色与亮色)的对比度下限: 可读下限加余量."""
    return LEGIBLE + TERM_MARGIN


def _rgb(v: str):
    return h(v.lstrip('#')[:6])


def tone(v, bg, min_cr: float):
    """终端彩色: 低于对比度下限时沿明度推到下限, 色相与饱和度不变; 够读的原样返回."""
    c = _rgb(v) if isinstance(v, str) else v
    min_cr = min_cr if on('term_floor') else None
    if min_cr is None or cr(c, bg) >= min_cr:
        return c
    L, C, H = oklch(c)
    s = sat(c)
    return fit(with_sat(L, s, H), bg, lo=min_cr, s=s)


def adapt(name: str, label: str, source: str, dark: bool, **over) -> dict:
    """按原主题自动适配: 底色, 正文, 光标, 选区与 16 色终端都取自补全段的中间主题, 再经看不清类步骤调整.

    over: 覆盖调色参数(如 syntax_max).
    """
    # 输入是补全段的中间主题(complete.py); 原主题文件名 source 只给规则池投票与保真度诊断用
    src = json.load(open(os.path.join(SOURCES, '..', 'full-theme', f'{name}-full.json'), encoding='utf-8'))
    c = src['colors']
    bg = _rgb(c['editor.background'])
    from gen_vscode import REGISTRY, source_fg
    fg = _rgb(source_fg(src, dark))
    if on('text_floor') and cr(fg, bg) < LEGIBLE:
        # 只在读不清时提到可读下限, 色相与饱和度不变
        fg = fit(fg, bg, lo=LEGIBLE + TERM_MARGIN)
    # 原主题没定义终端色(如 One Light)时, VS Code 显示的是注册表里的默认终端色, 照用
    reg = json.load(open(REGISTRY, encoding='utf-8'))['colors']
    ansi = lambda n: _rgb(c.get(f'terminal.ansi{n}') or reg[f'terminal.ansi{n}']['dark' if dark else 'light'])
    cursor = _rgb(c.get('editorCursor.foreground') or c.get('terminalCursor.foreground') or hx(fg))
    sel = c.get('editor.selectionBackground')
    sel = blend(_rgb(sel), bg, int(sel[7:9], 16) / 255 if len(sel) == 9 else 1) if sel else blend(cursor, bg, 0.25)
    token_min = SYNTAX_MIN
    return dict(
        name=name, label=label, dark=dark, gate=True, terminal=True, source=source,
        cap=0.10, token_min=token_min, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX if dark else LIGHT_SYNTAX_MAX,
        full=f'{name}-full.json', bg=bg, fg=fg, bold=fg, cursor=cursor, sel=sel,
        ui_src={n: tone(hx(ansi(n)), bg, token_min) for n in ANSI[1:7]},
        ansi=_ansi({n: tone(hx(ansi(n)), bg, term_accent_min(dark)) for n in ANSI[1:7]},
                   {n: tone(hx(ansi('Bright' + n)), bg, LEGIBLE) for n in ANSI[1:7]},
                   dict(Black=ansi('Black'), BrightBlack=ansi('BrightBlack'), White=ansi('White'), BrightWhite=ansi('BrightWhite')))) | over


def build() -> list[dict]:
    # cap: 彩度上限; token_min: 语法色相对编辑区底的对比度下限; comment_cr: 注释对比度(None 表示不调)
    T = []

    T += [adapt(n, f"C {n.split('-')[0].title()} {n.split('-')[1].title()}", f'{n}.json', dark=n.endswith('dark'))
          for n in ('one-dark', 'one-light', 'ayu-dark', 'ayu-light', 'sunlit-dark', 'sunlit-light')]
    T += [
        adapt('github-dark', 'C GitHub Dark', 'github-dark.json', dark=True),
        # GitHub Light 的蓝 / 绿原本就深, 与正文几乎一样黑; 最深的语法色压到正文的 0.9 倍, 彩色语法的亮度跨度回到柔和区间
        adapt('github-light', 'C GitHub Light', 'github-light.json', dark=False, syntax_max=0.9),
        adapt('dracula-dark', 'C Dracula Dark', 'dracula-dark.json', dark=True),
        # Dracula / Pale / Moka Light 的原主题由 design.py 以深色原主题为模板生成(Dracula 官方 Alucard 色板, Palenight 色相, 经典 Monokai 色板)
        adapt('dracula-light', 'C Dracula Light', 'dracula-light.json', dark=False),
        adapt('owl-dark', 'C Owl Dark', 'owl-dark.json', dark=True),
        adapt('owl-light', 'C Owl Light', 'owl-light.json', dark=False),
        adapt('moka-dark', 'C Moka Dark', 'moka-dark.json', dark=True),
        adapt('moka-light', 'C Moka Light', 'moka-light.json', dark=False),
        adapt('pale-dark', 'C Pale Dark', 'pale-dark.json', dark=True),
        adapt('pale-light', 'C Pale Light', 'pale-light.json', dark=False),
    ]

    # 终端彩色按终端口径(comfort.term_spec)补到下限; VS Code 界面图标按色相就近取终端色(gen_vscode.Mapper.accent / tint),
    # 用的是按语法色下限调的界面色源(ui_src), 终端色按终端口径改动时不牵连界面
    for t in T:
        t['ui_ansi'] = dict(t['ansi'])
        a, bg = t['ansi'], t['bg']
        t['ui_ansi'].update(t.pop('ui_src', {}))
        if not on('term_floor'):
            continue
        lo = term_accent_min(t['dark'])
        for n in TERM_COLORS:
            a[n] = fit(a[n], bg, lo=lo)
            if t['dark']:
                a['Bright' + n] = fit(a['Bright' + n], bg, lo=LEGIBLE + TERM_MARGIN)
    # 终端暗灰(90m)多用来显示注释与次要信息: 低于门禁 90m 下限时提上来
    for t in T:
        ts = term_spec(t['dark'])
        gray = t['ansi']['BrightBlack']
        if on('term_gray_floor') and cr(gray, t['bg']) < ts['gray'][0]:
            t['ansi']['BrightBlack'] = fit(gray, t['bg'], lo=ts['gray'][0] + TERM_MARGIN)
    # 终端选区(.terminal 的 SelectionColor, VS Code 的 terminal.selectionBackground / inactiveSelectionBackground):
    # 原主题多不定义, VS Code 回落到编辑区选区色, 浅色主题里几乎看不见; 一律按门禁终端范围的选区口径求色
    for t in T:
        ts, bg, fg, blue = term_spec(t['dark']), t['bg'], t['fg'], t['ansi']['Blue']
        # 原选区看得出且上面的字可读时沿用原选区
        if on('term_selection') and (cr(t['sel'], bg) < ts['selection'][0] or cr(fg, t['sel']) < ts['on_selection'][0]):
            t['sel'] = term_selection(bg, fg, blue, ts['selection'][0] + TERM_SEL_MARGIN, t['dark'])
            t['sel_inactive'] = term_selection(bg, fg, blue, ts['inactive_selection'][0] + TERM_SEL_INACTIVE_MARGIN, t['dark'])
            t['sel_changed'] = True
        else:
            # VS Code 失焦选区的缺省: 选区的一半透明度
            t['sel_inactive'] = blend(t['sel'], bg, 0.5)
    # 深色主题的近纯白压下来(white_cap); 语法色下限统一到 SYNTAX_MIN(终端色已在上面定好)
    for t in T:
        if on('white_cap') and t['dark']:
            for k in ('fg', 'bold', 'cursor'):
                t[k] = unwhite(t[k])
            t['ansi'] = {n: unwhite(c) for n, c in t['ansi'].items()}
        t['token_min'] = max(t['token_min'], SYNTAX_MIN)
        t.setdefault('syntax_max', SYNTAX_MAX if t['dark'] else LIGHT_SYNTAX_MAX)
    return T
