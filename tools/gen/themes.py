# 全部主题的定义, 是 VS Code 主题与 Terminal.app 主题的唯一数据来源.
#
# 每套主题都按补全段的中间主题 assets/full-theme/<name>-full.json(complete.py)适配: 底色, 正文, 光标, 选区与 16 色终端取自它,
# 再经 tools/gen/steps.py 登记的调色步骤调整; 步骤全关时这些值与 full 相同. Terminal 主题只用 bg / fg / bold / cursor / sel / ansi;
# VS Code 主题另用 sel / sel_inactive 作终端选区(term_selection 重算时才写回).
# 命名: <name>-dark / <name>-light(与 assets/source/ 的原主题同名), 显示名 C <Name> Dark / Light.
import json, math, os, re

from colorlib import (unwhite, amber, blend, blue_light, cr, de2000, deneon, fit, from_oklch, h, hx, lum, oklch, sat, shift, soften,
                      toward_bg, tune, unextreme, with_sat)
from comfort import BRIGHT_TINT_L, LIGHT_BG_MAX, TERM_COLORS, TERM_HUES, term_spec
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
# 饱和度(相对彩度)的平滑压缩: 不再有绝对彩度上限. knee 以下保留原主题的饱和度, 超出部分只保留 0.4 倍(原来更艳的仍更艳);
# 原主题里的彩色(彩度 > 0.035)不低于 floor, 不压成灰. 界面图标与状态色的 knee 更低一些; 大面积底色仍按 cap(彩度)与对比度安静处理
SYN_KNEE, SYN_FLOOR = 0.80, 0.50
UI_KNEE, UI_FLOOR = 0.70, 0.40
# 荧光度(colorlib.neon)目标: 门禁理想 0.05, 留余量; 高明度的黄绿 / 青先降明度再降彩度
NEON_TARGET = 0.045
# 终端色的生成目标一律取门禁终端范围(comfort.term_spec)的理想值, 留余量防 hex 取整, 不借用语法色 / 注释的口径;
# 这几项深浅相同, 取深色的表即可. knee 是压缩曲线的形状, 门禁没有对应指标
_TS = term_spec(True)
TERM_KNEE = 0.85
TERM_FLOOR = _TS['sat_min'][0] + 0.05
TERM_NEON = _TS['neon'][1] - 0.005
# 6 个普通色两两色差的目标(CIEDE2000): 不足时在色槽范围内转色相拉开
TERM_DISTINCT = _TS['distinct'][0] + 1
# 对比度目标的余量; 90m 暗灰对比度 = 正文 / TERM_GRAY_RATIO, 再夹进门禁 90m 的理想区间
TERM_MARGIN = 0.05
TERM_GRAY_RATIO = 1.85


# 选区对比度目标在门禁 选区 / 失焦选区 理想下限上留的余量: 程序自己铺的浅色块(如 Codex 输入区)比终端底再近一档, 留足才看得出
TERM_SEL_MARGIN, TERM_SEL_INACTIVE_MARGIN = 0.1, 0.05


def term_selection(bg, fg, blue, target: float, dark: bool):
    """终端选区: 终端蓝按比例混进底色, 推到与底对比度 >= target; 亮色块饱和度压到门禁 亮底饱和度 理想上限以内,
    压在上面的正文不低于 选区上的字 的理想下限(达不到时停在能保住正文的最强一档). 正文本身只比理想下限高一点时(如 Sunlit 4.5~4.75)
    选区稍一显出来字就不够理想下限, 会停在底色上等于没有选区; 这时正文改按 选区上的字 的限值(3.5, 同编辑区 高亮上的字)求色."""
    ts = term_spec(dark)
    cap = ts['bright_tint'][1] - 0.02
    for on_min in (ts['on_selection'][0] + TERM_MARGIN, ts['on_selection'][2] + TERM_MARGIN):
        best = bg
        for i in range(1, 201):
            c = blend(blue, bg, i / 200)
            L, C, H = oklch(c)
            if on('bright_tint') and L > BRIGHT_TINT_L and sat(c) > cap:
                c = with_sat(L, cap, H)
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
# 浅色底: 亮度目标带; 上限 0.87 取 v0.0.1 手调浅色底的水平(One Light #F0F0F2 为 0.873), 只把纯白一类的底压暗, 不再按门禁理想 0.82 压;
# 线性蓝光上限(门禁蓝光量 = 0.85 x 底 + 0.15 x 文字, 理想 <= 0.68);
# 中性或偏暖的底往暖白偏(色相 WARM_HUE, 彩度最多 WARM_MAX_C), 冷色调的底(如 Pale 的薰衣草)降彩度保留色相, 仍超就在亮度带内降亮度
# 各步骤是否执行见 steps.py(light_bg / bg_hue / bg_blue)
LIGHT_BG_BAND = (0.72, 0.87)
BG_BLUE_MAX = 0.70
WARM_HUE, WARM_MAX_C = math.radians(80), 0.022
# 原主题是近白中性底的浅色主题: 统一偏暖白会让几套底色完全相同, 改为各自朝主题色(界面强调色; Moka 取 Monokai 绿)偏移,
# 彩度与亮度带一致, 只有色相不同(度)
THEME_BG_C = 0.012
THEME_BG_HUE = {'one-light': 270, 'github-light': 257, 'ayu-light': 67, 'owl-light': 187, 'moka-light': 130}


def _rgb(v: str):
    return h(v.lstrip('#')[:6])


def tone(v, bg, min_cr: float, dl: float = 0.0):
    """终端彩色: 原色饱和度经平滑压缩(不封顶), 明度偏移 dl 后推到对比度下限; 浅色主题压深的黄朝琥珀偏, 不成橄榄绿."""
    c = _rgb(v) if isinstance(v, str) else v
    L, C, H = oklch(c)
    s = soften(sat(c), TERM_KNEE, TERM_FLOOR if C > 0.035 else 0.0) if on('term_soften') else sat(c)
    dl = dl if on('term_bright_shift') else 0.0
    min_cr = min_cr if on('term_floor') else None
    # 饱和度, 明度都不动且对比度已够时原样返回, 不经 OKLCH 往返
    if not on('term_soften') and not dl and (min_cr is None or cr(c, bg) >= min_cr):
        return c
    dark = lum(bg) < 0.2
    out = fit(with_sat(L + dl, s, H), bg, lo=min_cr, s=s)
    H2 = amber(H, oklch(out)[0], dark) if on('amber') else H
    if H2 != H:
        out = fit(with_sat(oklch(out)[0], s, H2), bg, lo=min_cr, s=s)
    return out


def _hue_into(deg: float, rng: tuple, margin: float = 4) -> float:
    """把色相挪进槽位范围(两端各留 margin 度), 已在范围内的不动."""
    lo, hi = rng
    span = (hi - lo) % 360
    off = (deg - lo) % 360
    if margin <= off <= span - margin:
        return deg
    to_lo, to_hi = (lo - deg) % 360, (deg - hi) % 360
    return (lo + margin) % 360 if min(to_lo, 360 - to_lo) < min(to_hi, 360 - to_hi) else (hi - margin) % 360


def vivid(c, slot: str):
    """终端彩色: 色相挪回槽位, 饱和度不低于 TERM_FLOOR, 明度不变."""
    L, C, H = oklch(c)
    s = max(sat(c), TERM_FLOOR)
    return with_sat(L, s, math.radians(_hue_into(math.degrees(H) % 360, TERM_HUES[slot])))


def separate_ansi(a: dict, bg, step: float = 3) -> None:
    """普通色两两色差不足 TERM_DISTINCT 时, 在色槽范围内反向转动这对颜色的色相, 对比度与饱和度保持不变."""
    for _ in range(12):
        pairs = [(de2000(a[x], a[y]), x, y) for i, x in enumerate(TERM_COLORS) for y in TERM_COLORS[i + 1:]]
        d, x, y = min(pairs)
        if d >= TERM_DISTINCT:
            return
        hx_, hy = (math.degrees(oklch(a[n])[2]) % 360 for n in (x, y))
        diff = (hy - hx_ + 180) % 360 - 180  # y 相对 x 的有向色相差
        sign = 1 if diff >= 0 else -1
        moved = False
        for n, dirn in ((x, -sign), (y, sign)):
            L, C, H = oklch(a[n])
            deg = (math.degrees(H) + dirn * step) % 360
            if _hue_into(deg, TERM_HUES[n], 2) != deg:
                continue
            target, s = cr(a[n], bg), sat(a[n])
            a[n], moved = fit(with_sat(L, s, math.radians(deg)), bg, lo=target, hi=target, s=s), True
        if not moved:
            return


def fit_bg(c, dark: bool, hue: float | None = None):
    """深色: 底亮度不低于 0.016(近纯黑时字的光晕重); 色相与彩度不变.
    浅色: 亮度落进 LIGHT_BG_BAND, 再把线性蓝光压到 BG_BLUE_MAX: 中性或偏暖的底往暖白偏, 冷色调的底降彩度, 仍超就降亮度."""
    L, C, H = oklch(c)
    band = on('light_bg')
    if dark:
        while on('bg_dark_floor') and lum(c) < 0.016 and 0 < L < 1:
            L += 0.002
            c = from_oklch(L, C, H)
        return c
    if hue is not None and on('bg_hue'):
        # 朝主题色偏: 色相 hue, 彩度 THEME_BG_C, 亮度落进 LIGHT_BG_BAND; 不再往暖白偏
        H, C = math.radians(hue), THEME_BG_C
        c = from_oklch(L, C, H)
        while band and lum(c) > LIGHT_BG_BAND[1] and L > 0:
            L -= 0.002
            c = from_oklch(L, C, H)
        while band and lum(c) < LIGHT_BG_BAND[0] and L < 1:
            L += 0.002
            c = from_oklch(L, C, H)
        return c
    deg = math.degrees(H) % 360
    warmish = C < 0.012 or 30 <= deg <= 110
    if not (band or on('bg_hue') or on('bg_blue')):
        return c
    if C < 0.012 and on('bg_hue'):
        H = WARM_HUE
    c = from_oklch(L, C, H)
    while band and lum(c) > LIGHT_BG_BAND[1] and L > 0:
        L -= 0.002
        c = from_oklch(L, C, H)
    while band and lum(c) < LIGHT_BG_BAND[0] and L < 1:
        L += 0.002
        c = from_oklch(L, C, H)
    for _ in range(500 if on('bg_blue') else 0):
        if blue_light(c) <= BG_BLUE_MAX:
            break
        if warmish and C < WARM_MAX_C:
            C += 0.001
        elif not warmish and C > 0.012:
            C -= 0.001
        elif lum(c) > LIGHT_BG_BAND[0]:
            L -= 0.002
        else:
            break
        c = from_oklch(L, C, H)
    return c


def adapt(name: str, label: str, source: str, dark: bool, text: float | None = None, **over) -> dict:
    """按原主题自动适配: 底色, 正文, 光标, 选区与 16 色终端都取自原主题的 colors, 再按门禁口径调校.

    text: 正文目标对比度, 默认深色 7.0, 浅色 8.0; 原主题正文偏亮压下去, 偏暗提上来.
    over: 覆盖调色参数(如 syntax_max).
    """
    # 输入是补全段的中间主题(complete.py); 原主题文件名 source 只给规则池投票与保真度诊断用
    src = json.load(open(os.path.join(SOURCES, '..', 'full-theme', f'{name}-full.json'), encoding='utf-8'))
    c = src['colors']
    bg = fit_bg(_rgb(c['editor.background']), dark, THEME_BG_HUE.get(name))
    from gen_vscode import REGISTRY, source_fg
    fg = _rgb(source_fg(src, dark))
    target = text or (7.0 if dark else 8.0)
    if cr(fg, bg) > target:
        fg = toward_bg(fg, bg, target) if on('text_cap') else fg
    elif on('text_floor') and cr(fg, bg) < LEGIBLE:
        # 只在读不清时提到可读下限, 色相与饱和度不变
        fg = fit(fg, bg, lo=LEGIBLE + TERM_MARGIN)
    # 原主题没定义终端色(如 One Light)时, VS Code 显示的是注册表里的默认终端色, 照用
    reg = json.load(open(REGISTRY, encoding='utf-8'))['colors']
    ansi = lambda n: _rgb(c.get(f'terminal.ansi{n}') or reg[f'terminal.ansi{n}']['dark' if dark else 'light'])
    cursor = _rgb(c.get('editorCursor.foreground') or c.get('terminalCursor.foreground') or hx(fg))
    sel = c.get('editor.selectionBackground')
    sel = blend(_rgb(sel), bg, int(sel[7:9], 16) / 255 if len(sel) == 9 else 1) if sel else blend(cursor, bg, 0.25)
    bright, dl = LEGIBLE, (0.05 if dark else -0.06)
    # 彩底上的字(徽标)要靠终端黑 / 白撑对比度: 黑至少比底再深一档(浅色主题比正文再深), 亮白至少比正文亮
    darker = lambda a, b: a if lum(a) < lum(b) or not on('term_badge_bw') else b
    black = darker(ansi('Black'), shift(bg, -0.05) if dark else shift(fg, -0.05))
    lighter = lambda a, b: a if lum(a) > lum(b) or not on('term_badge_bw') else b
    # 深色主题亮白比正文亮; 浅色主题的彩色偏深, 亮白要比底色再亮一档, 才能在彩底上写白字
    white = lighter(ansi('BrightWhite'), shift(fg, 0.08) if dark else shift(bg, 0.04))
    token_min = SYNTAX_MIN
    return dict(
        name=name, label=label, dark=dark, gate=True, terminal=True, source=source,
        cap=0.10, token_min=token_min, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX if dark else LIGHT_SYNTAX_MAX,
        full=f'{name}-full.json', bg=bg, fg=fg, bold=fg, cursor=cursor, sel=sel,
        ui_src={n: tone(hx(ansi(n)), bg, token_min) for n in ANSI[1:7]},
        ansi=_ansi({n: tone(hx(ansi(n)), bg, term_accent_min(dark)) for n in ANSI[1:7]},
                   {n: tone(hx(ansi('Bright' + n)), bg, bright, dl) for n in ANSI[1:7]},
                   dict(Black=black, BrightBlack=ansi('BrightBlack'), White=ansi('White'), BrightWhite=white))) | over


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

    # 终端彩色不比正文更刺眼(深色主题): 普通色 <= 正文, 亮色 <= 正文 x 门禁 最亮彩字/正文 理想上限, white <= 正文 x 1.05,
    # 亮白 <= 正文 x 1.25; 原主题的亮黄 / 亮青 / 白常接近纯白, 满屏 ls / git 输出时成了亮块; 压暗时饱和度保持(fit), 不变灰.
    # 浅色主题的 white 要是浅色(有的浅色原主题把它设成了近黑)
    for t in T:
        a, bg, text = t['ansi'], t['bg'], cr(t['fg'], t['bg'])
        if t['dark']:
            if not on('term_glare_cap'):
                continue
            for n in ANSI[1:7]:
                a[n] = fit(a[n], bg, hi=text)
                a['Bright' + n] = fit(a['Bright' + n], bg, hi=text * term_spec(True)['glare'][1])
            a['White'] = toward_bg(a['White'], bg, text * 1.05)
            a['BrightWhite'] = toward_bg(a['BrightWhite'], bg, text * 1.25)
        elif on('term_white_light') and lum(a['White']) < 0.35:
            a['White'] = blend(t['fg'], bg, 0.25)
    # 终端彩色(口径见 comfort.specs 的终端范围): 色相回槽, 饱和度不低于下限, 普通色两两拉开, 对比度回到口径, 再去荧光感
    # VS Code 界面图标按色相就近取终端色(gen_vscode.Mapper.accent / tint); 取本步之前的色板, 免得色相微调让图标换到另一个色槽
    # 自动适配的主题另有按语法色下限调的界面色源(ui_src), 终端色按终端口径改动时不牵连界面
    for t in T:
        t['ui_ansi'] = dict(t['ansi'])
        a, bg, text = t['ansi'], t['bg'], cr(t['fg'], t['bg'])
        for n, c in t.pop('ui_src', {}).items():
            t['ui_ansi'][n] = fit(c, bg, hi=text) if t['dark'] and on('ui_text_cap') else c
        if on('term_hue_slot'):
            for n in TERM_COLORS:
                a[n], a['Bright' + n] = vivid(a[n], n), vivid(a['Bright' + n], n)
        if on('term_separate'):
            separate_ansi(a, bg)
        ts = term_spec(t['dark'])
        floor, cap = on('term_floor'), on('term_glare_cap')
        lo = term_accent_min(t['dark'])
        # 普通色上限: 不超过正文, 且 最亮 / 最暗 不超过门禁 彩字跨度 的理想上限
        hi = min(text, lo * (ts['accent_span'][1] - TERM_MARGIN))
        bright_lo = LEGIBLE + TERM_MARGIN
        dn = lambda c, m: deneon(c, TERM_NEON, bg, m) if on('neon') else c
        for n in TERM_COLORS:
            if floor or cap:
                a[n] = fit(a[n], bg, lo=lo if floor else None, hi=hi if cap else None)
            a[n] = dn(a[n], lo)
            b = a['Bright' + n]
            if t['dark'] and (floor or cap):
                b = fit(b, bg, lo=bright_lo if floor else None, hi=text * ts['glare'][1] if cap else None)
            a['Bright' + n] = dn(b, bright_lo)
    # 终端暗灰(90m)多用来显示注释与次要信息: 正文 / TERM_GRAY_RATIO, 夹进门禁 90m 与 90m上限 的理想区间
    for t in T:
        ts = term_spec(t['dark'])
        gray = t['ansi']['BrightBlack']
        if on('term_gray_fit'):
            target = min(ts['gray_hi'][1], max(ts['gray'][0], cr(t['fg'], t['bg']) / TERM_GRAY_RATIO))
            gray = tune(hx(gray), t['bg'], 0.03, target)
            t['ansi']['BrightBlack'] = toward_bg(gray, t['bg'], target)
        elif on('term_gray_floor') and cr(gray, t['bg']) < ts['gray'][0]:
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
    # 不用纯黑 / 乌黑, 纯白 / 亮白(口径见 comfort 的护眼维度); 语法色下限统一到 SYNTAX_MIN(终端色已在上面定好)
    for t in T:
        if on('white_cap') and t['dark']:
            for k in ('fg', 'bold', 'cursor'):
                t[k] = unwhite(t[k])
            t['ansi'] = {n: unwhite(c) for n, c in t['ansi'].items()}
        if on('unextreme'):
            for k in ('bg', 'fg', 'bold', 'cursor', 'sel', 'sel_inactive'):
                t[k] = unextreme(t[k])
            t['ansi'] = {n: unextreme(c) for n, c in t['ansi'].items()}
        t['token_min'] = max(t['token_min'], SYNTAX_MIN)
        t.setdefault('syntax_max', SYNTAX_MAX if t['dark'] else LIGHT_SYNTAX_MAX)
    return T
