# 全部主题的定义, 是 VS Code 主题与 Terminal.app 主题的唯一数据来源.
#
# VS Code 主题以 tools/sources/ 下的原主题为模板: 界面键逐色变换, 语法规则由规则池(pool.py)按本主题的角色色生成;
# 本文件给出变换目标(底色, 前景, 16 色终端)与调色参数. Terminal 主题只用 bg / fg / bold / cursor / sel / ansi.
# 命名: comfort-<name>-dark / comfort-<name>-light, 显示名 Comfort <Name> Dark / Light; 原主题文件为 tools/sources/<name>-dark|light.json.
import json, os, re

from colorlib import blend, cr, from_oklch, h, hx, lum, oklch, shift, toward_bg, tune

SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources')

ANSI = ['Black', 'Red', 'Green', 'Yellow', 'Blue', 'Magenta', 'Cyan', 'White']


def _ansi(normal: dict, bright: dict, grays: dict) -> dict:
    return {**normal, **{'Bright' + k: v for k, v in bright.items()}, **grays}


# One Dark Pro 原版的终端色(terminal.ansi*)
ODP_NORMAL = dict(Red='#E05561', Green='#8CC265', Yellow='#D18F52', Blue='#4AA5F0', Magenta='#C162DE', Cyan='#42B3C2')
ODP_BRIGHT = dict(Red='#FF616E', Green='#A5E075', Yellow='#F0A45D', Blue='#4DC4FF', Magenta='#DE73FF', Cyan='#4CD1E0')

SOL_NORMAL = dict(Red='DC322F', Green='859900', Yellow='B58900', Blue='268BD2', Magenta='D33682', Cyan='2AA198')
# 亮红沿用官方 orange, 亮紫沿用官方 violet
SOL_BRIGHT = dict(Red='CB4B16', Green='859900', Yellow='B58900', Blue='268BD2', Magenta='6C71C4', Cyan='2AA198')


# 注释对比度: 'auto' 表示随正文联动(正文 / 1.85, 限制在 3.4~4.2, 见 gen_vscode.py), 偏低提升, 偏高压低
COMMENT_CR = 'auto'
# 深色主题语法色对比度上限 = 正文对比度 x SYNTAX_MAX: 彩色不比正文更抢眼
SYNTAX_MAX = 1.0


def _rgb(v: str):
    return h(v.lstrip('#')[:6])


def fit_bg(c, dark: bool):
    # 底亮度落到防疲劳理想区间: 深色 >= 0.016(近纯黑时字的光晕重), 浅色 <= 0.85(近纯白眩光大); 色相与彩度不变
    L, C, H = oklch(c)
    while (lum(c) < 0.016 if dark else lum(c) > 0.85) and 0 < L < 1:
        L += 0.002 if dark else -0.002
        c = from_oklch(L, C, H)
    return c


def adapt(name: str, label: str, source: str, dark: bool, text: float | None = None) -> dict:
    """按原主题自动适配: 底色, 正文, 光标, 选区与 16 色终端都取自原主题的 colors, 再按门禁口径调校.

    text: 正文目标对比度, 默认深色 7.0, 浅色 8.5; 原主题正文偏亮压下去, 偏暗提上来.
    """
    s = open(os.path.join(SOURCES, source), encoding='utf-8').read()
    src = json.loads(re.sub(r',(\s*[}\]])', r'\1', re.sub(r'^\s*//.*$', '', s, flags=re.M)))
    c = src['colors']
    bg = fit_bg(_rgb(c['editor.background']), dark)
    from gen_vscode import source_fg
    fg = _rgb(source_fg(src, dark))
    target = text or (7.0 if dark else 8.5)
    fg = toward_bg(fg, bg, target) if cr(fg, bg) > target else tune(hx(fg), bg, 0.03, target)
    ansi = lambda n: _rgb(c[f'terminal.ansi{n}'])
    cursor = _rgb(c.get('editorCursor.foreground') or c.get('terminalCursor.foreground') or hx(fg))
    sel = c.get('editor.selectionBackground')
    sel = blend(_rgb(sel), bg, int(sel[7:9], 16) / 255 if len(sel) == 9 else 1) if sel else blend(cursor, bg, 0.25)
    bright, dl = (6.5, 0.05) if dark else (6.0, -0.06)
    # 彩底上的字(徽标)要靠终端黑 / 白撑对比度: 黑至少比底再深一档(浅色主题比正文再深), 亮白至少比正文亮
    darker = lambda a, b: a if lum(a) < lum(b) else b
    black = darker(ansi('Black'), shift(bg, -0.05) if dark else shift(fg, -0.05))
    lighter = lambda a, b: a if lum(a) > lum(b) else b
    # 深色主题亮白比正文亮; 浅色主题的彩色偏深, 亮白要比底色再亮一档, 才能在彩底上写白字
    white = lighter(ansi('BrightWhite'), shift(fg, 0.08) if dark else shift(bg, 0.04))
    # 浅色主题正文 8.5, 语法色下限 5.0 时彩色语法的亮度跨度约 1.7, 落在柔和限值内
    token_min = 4.8 if dark else 5.0
    return dict(
        name=name, label=label, dark=dark, gate=True, terminal=True, source=source,
        cap=0.10, token_min=token_min, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX,
        bg=bg, fg=fg, bold=shift(fg, 0.08 if dark else -0.08), cursor=cursor, sel=sel,
        ansi=_ansi({n: tune(hx(ansi(n)), bg, 0.10, token_min) for n in ANSI[1:7]},
                   {n: tune(hx(ansi('Bright' + n)), bg, 0.10, bright, dl) for n in ANSI[1:7]},
                   dict(Black=black, BrightBlack=ansi('BrightBlack'), White=ansi('White'), BrightWhite=white)))


def build() -> list[dict]:
    # cap: 彩度上限; token_min: 语法色相对编辑区底的对比度下限; comment_cr: 注释对比度(None 表示不调)
    T = []

    # ---- Comfort One Dark: One Dark Pro 的完整护眼适配. 底色与正文沿用原版;
    #      注释随正文联动, 语法色不亮过正文, 彩度封顶; 终端色取 One Dark Pro 自己的终端色板(偏橙的黄)调校 ----
    bg = h('#282C34')
    T.append(dict(name='comfort-one-dark', label='Comfort One Dark', dark=True, gate=True, terminal=True,
                  source='one-dark.json', cap=0.10, token_min=4.5, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX,
                  bg=bg, fg=h('#ABB2BF'), bold=h('#D7DAE0'), cursor=h('#528BFF'), sel=h('#3E4451'),
                  ansi=_ansi({k: tune(v, bg, 0.10, 4.5) for k, v in ODP_NORMAL.items()},
                             {k: tune(v, bg, 0.10, 6.5, 0.05) for k, v in ODP_BRIGHT.items()},
                             dict(Black=h('#21252B'), BrightBlack=h('#7F848E'), White=h('#D7DAE0'), BrightWhite=h('#E6E6E6')))))

    # ---- Comfort One Light: akamud One Light 2.3.0 的完整护眼适配, 与 Comfort One Dark 同方案;
    #      底 #FAFAFA(亮度 0.956)眩光偏大, 压暗为 #F0F0F2(0.873), 正文压到对比度 8.5;
    #      原版没有终端色, 终端取原版语法色同口径调校, 亮白取原版底色 #FAFAFA 保证彩色底上的白字可读 ----
    bg = h('#F0F0F2')
    acc = dict(Red='E45649', Green='50A14F', Yellow='C18401', Blue='4078F2', Magenta='A626A4', Cyan='0184BC')
    T.append(dict(name='comfort-one-light', label='Comfort One Light', dark=False, gate=True, terminal=True,
                  source='one-light.json', cap=0.10, token_min=4.5, comment_cr=COMMENT_CR,
                  bg=bg, fg=toward_bg(h('#383A42'), bg, 8.5), bold=h('#232324'), cursor=h('#526FFF'),
                  sel=blend(h('#526FFF'), bg, 0.18),
                  ansi=_ansi({n: tune(v, bg, 0.10, 4.5) for n, v in acc.items()},
                             {n: tune(v, bg, 0.10, 6.0, -0.06) for n, v in acc.items()},
                             dict(Black=h('#383A42'), BrightBlack=tune('A0A1A7', bg, 0.02, 3.2), White=h('#CDCED3'), BrightWhite=h('#FAFAFA')))))

    # ---- ayu-dark: ayu Mirage, 底 lift #242936 ----
    bg = h('#242936')
    nor = dict(Red='F06B5C', Green='BFE76D', Yellow='E6B752', Blue='3BBBF4', Magenta='D09FFD', Cyan='84CEB5')
    brt = dict(Red='F39184', Green='D5FF80', Yellow='FFCD66', Blue='73D0FF', Magenta='DFBFFF', Cyan='95E6CB')
    T.append(dict(
        name='comfort-ayu-dark', label='Comfort Ayu Dark', dark=True, gate=True, terminal=True, source='ayu-dark.json',
        cap=0.10, token_min=5.0, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX,
        bg=bg, fg=toward_bg(h('#CCCAC2'), bg, 7.5), bold=h('#E6E1CF'), cursor=h('#FFCC66'), sel=blend(h('#409FFF'), bg, 0.25),
        ansi=_ansi({n: tune(v, bg, 0.10, 5.0) for n, v in nor.items()},
                   {n: tune(v, bg, 0.10, 7.0) for n, v in brt.items()},
                   # 官方 black 为近纯黑 #0A0000, 改用 Mirage 的 sunk 面色, 仍够深以保证彩底黑字
                   dict(Black=h('#171B24'), BrightBlack=tune('707A8C', bg, 0.03, 3.4), White=h('#D2D6DC'), BrightWhite=h('#E3E6EA')))))

    # ---- ayu-light: ayu Light, 底由 #FCFCFC 压暗到 #EFF0F2(底亮度 0.87), 字 #5C6166 加深到对比度 7.0 ----
    bg = h('#EFF0F2')
    nor = dict(Red='F07171', Green='86B300', Yellow='EBA400', Blue='22A4E6', Magenta='A37ACC', Cyan='4CBF99')
    T.append(dict(
        name='comfort-ayu-light', label='Comfort Ayu Light', dark=False, gate=True, terminal=True, source='ayu-light.json',
        cap=0.10, token_min=4.8, comment_cr=COMMENT_CR,
        bg=bg, fg=h('#4C5158'), bold=h('#33373D'), cursor=h('#F29718'), sel=blend(h('#035BD6'), bg, 0.15),
        ansi=_ansi({n: tune(v, bg, 0.10, 4.8) for n, v in nor.items()},
                   {n: tune(v, bg, 0.10, 6.0, -0.06) for n, v in nor.items()},
                   dict(Black=h('#242936'), BrightBlack=tune('ADAEB1', bg, 0.02, 3.2), White=h('#C9CDD3'), BrightWhite=h('#DFE2E7')))))

    # ---- Comfort Sunlit Dark(参考 Solarized Dark): 官方 base03 底, 正文比 base1 稍亮, 对比度 7.0 ----
    bg = h('#002B36')
    T.append(dict(
        name='comfort-sunlit-dark', label='Comfort Sunlit Dark', dark=True, gate=True, terminal=True, source='sunlit-dark.json',
        cap=0.10, token_min=5.0, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX,
        bg=bg, fg=h('#A6B4B4'), bold=h('#EEE8D5'), cursor=h('#93A1A1'), sel=h('#0A4A5A'),
        ansi=_ansi({n: tune(v, bg, 0.10, 5.0) for n, v in SOL_NORMAL.items()},
                   {n: tune(v, bg, 0.10, 6.5, 0.06) for n, v in SOL_BRIGHT.items()},
                   dict(Black=h('#073642'), BrightBlack=tune('657B83', bg, 0.03, 3.4), White=h('#D3CDBB'), BrightWhite=h('#EEE8D5')))))

    # ---- Comfort Sunlit Light(参考 Solarized Light): base3 #FDF6E3 压暗为 #F5EEDA, 正文取 base01 与 base02 之间, 对比度 7.0 ----
    bg = h('#F5EEDA')
    T.append(dict(
        name='comfort-sunlit-light', label='Comfort Sunlit Light', dark=False, gate=True, terminal=True, source='sunlit-light.json',
        cap=0.10, token_min=4.8, comment_cr=COMMENT_CR,
        bg=bg, fg=h('#3E5259'), bold=h('#073642'), cursor=h('#586E75'), sel=h('#E3D9BC'),
        ansi=_ansi({n: tune(v, bg, 0.10, 4.8) for n, v in SOL_NORMAL.items()},
                   {n: tune(v, bg, 0.10, 6.0, -0.06) for n, v in SOL_BRIGHT.items()},
                   dict(Black=h('#073642'), BrightBlack=tune('93A1A1', bg, 0.03, 3.2), White=h('#DDD5BC'), BrightWhite=h('#EBE4CE')))))

    # ---- 按原主题自动适配的主题(adapt): 底色, 正文与终端色取自原主题, 再按门禁口径调校 ----
    T += [
        adapt('comfort-github-dark', 'Comfort GitHub Dark', 'github-dark.json', dark=True),
        adapt('comfort-github-light', 'Comfort GitHub Light', 'github-light.json', dark=False),
        adapt('comfort-dracula-dark', 'Comfort Dracula Dark', 'dracula-dark.json', dark=True),
        adapt('comfort-night-owl-dark', 'Comfort Night Owl Dark', 'night-owl-dark.json', dark=True),
        adapt('comfort-night-owl-light', 'Comfort Night Owl Light', 'night-owl-light.json', dark=False),
        adapt('comfort-one-monokai-dark', 'Comfort One Monokai Dark', 'one-monokai-dark.json', dark=True),
        adapt('comfort-pale-night-dark', 'Comfort Pale Night Dark', 'pale-night-dark.json', dark=True),
    ]

    # 终端暗灰(90m)多用来显示注释与次要信息, 与注释同口径: 正文 / 1.85, 限制在 3.4~4.2
    for t in T:
        target = min(4.2, max(3.4, cr(t['fg'], t['bg']) / 1.85))
        gray = tune(hx(t['ansi']['BrightBlack']), t['bg'], 0.03, target)
        t['ansi']['BrightBlack'] = toward_bg(gray, t['bg'], target)
    return T
