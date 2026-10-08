# 7 套主题的定义, 是 VS Code 主题与 Terminal.app 主题的唯一数据来源.
#
# VS Code 主题以 tools/sources/ 下的原主题为模板, 保留其全部界面键与语法规则, 由 gen_vscode.py 逐色变换;
# 本文件给出变换目标(底色, 前景, 16 色终端)与调色参数. Terminal 主题只用 bg / fg / bold / cursor / sel / ansi.
# one-dark-pro 例外: 原版逐字保留, 只补原版未定义的硬编码默认色键, 不参与达标门禁.
from colorlib import blend, h, hx, tune

ANSI = ['Black', 'Red', 'Green', 'Yellow', 'Blue', 'Magenta', 'Cyan', 'White']


def _ansi(normal: dict, bright: dict, grays: dict) -> dict:
    return {**normal, **{'Bright' + k: v for k, v in bright.items()}, **grays}


# One Dark Pro 原版的终端色(terminal.ansi*)
ODP_NORMAL = dict(Red='#E05561', Green='#8CC265', Yellow='#D18F52', Blue='#4AA5F0', Magenta='#C162DE', Cyan='#42B3C2')
ODP_BRIGHT = dict(Red='#FF616E', Green='#A5E075', Yellow='#F0A45D', Blue='#4DC4FF', Magenta='#DE73FF', Cyan='#4CD1E0')

SOL_NORMAL = dict(Red='DC322F', Green='859900', Yellow='B58900', Blue='268BD2', Magenta='D33682', Cyan='2AA198')
# 亮红沿用官方 orange, 亮紫沿用官方 violet
SOL_BRIGHT = dict(Red='CB4B16', Green='859900', Yellow='B58900', Blue='268BD2', Magenta='6C71C4', Cyan='2AA198')


# 注释对比度: 所有 Comfort 主题统一到这个值, 偏低提升, 偏高压低
COMMENT_CR = 3.2
# 深色主题语法色对比度上限 = 正文对比度 x SYNTAX_MAX
SYNTAX_MAX = 1.1


def build() -> list[dict]:
    # cap: 彩度上限; token_min: 语法色相对编辑区底的对比度下限; comment_cr: 注释对比度(None 表示不调)
    T = []

    # ---- One Dark Pro Lite: 原版逐字保留, 只补原版未定义的硬编码默认色键, 补色取原版自己的颜色 ----
    bg = h('#282C34')
    odp_ansi = _ansi({k: h(v) for k, v in ODP_NORMAL.items()}, {k: h(v) for k, v in ODP_BRIGHT.items()},
                     dict(Black=h('#3F4451'), BrightBlack=h('#4F5666'), White=h('#D7DAE0'), BrightWhite=h('#E6E6E6')))
    T.append(dict(name='one-dark-pro', label='One Dark Pro Lite', dark=True, gate=False, terminal=False,
                  source='one-dark-pro.json', verbatim=True, cap=1.0, token_min=0,
                  bg=bg, fg=h('#ABB2BF'), cursor=h('#528BFF'), ansi=odp_ansi))

    # ---- one-dark: 底同 One Dark Pro, 正文略提亮, 彩色降彩度 ----
    bg = h('#282C34')
    acc = dict(Red='E06C75', Green='98C379', Yellow='E5C07B', Blue='61AFEF', Magenta='C678DD', Cyan='56B6C2')
    T.append(dict(
        name='one-dark', label='Comfort One Dark', dark=True, gate=True, terminal=True, source='one-dark-pro.json',
        cap=0.13, token_min=4.8, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX,
        bg=bg, fg=tune('ABB2BF', bg, 0.03, 7.5), bold=h('#D7DAE0'), cursor=h('#528BFF'), sel=h('#3E4451'),
        ansi=_ansi({n: tune(v, bg, 0.13, 4.8) for n, v in acc.items()},
                   {n: tune(v, bg, 0.12, 6.5, 0.05) for n, v in acc.items()},
                   dict(Black=h('#21252B'), BrightBlack=h('#7F848E'), White=h('#C8CCD4'), BrightWhite=h('#E6E6E6')))))

    # ---- one-light: 底 #FAFAFA 压暗为 #F0F0F2, 彩色降彩度, 亮色为同色相加深 ----
    bg = h('#F0F0F2')
    acc = dict(Red='E45649', Green='50A14F', Yellow='C18401', Blue='4078F2', Magenta='A626A4', Cyan='0184BC')
    T.append(dict(
        name='one-light', label='Comfort One Light', dark=False, gate=True, terminal=True, source='one-light.json',
        cap=0.14, token_min=4.8, comment_cr=COMMENT_CR,
        bg=bg, fg=h('#383A42'), bold=h('#232324'), cursor=h('#526FFF'), sel=blend(h('#526FFF'), bg, 0.18),
        ansi=_ansi({n: tune(v, bg, 0.14, 4.8) for n, v in acc.items()},
                   {n: tune(v, bg, 0.13, 6.0, -0.06) for n, v in acc.items()},
                   dict(Black=h('#383A42'), BrightBlack=tune('A0A1A7', bg, 0.02, 3.2), White=h('#CDCED3'), BrightWhite=h('#E0E0E4')))))

    # ---- ayu-dark: ayu Mirage, 底 lift #242936 ----
    bg = h('#242936')
    nor = dict(Red='F06B5C', Green='BFE76D', Yellow='E6B752', Blue='3BBBF4', Magenta='D09FFD', Cyan='84CEB5')
    brt = dict(Red='F39184', Green='D5FF80', Yellow='FFCD66', Blue='73D0FF', Magenta='DFBFFF', Cyan='95E6CB')
    T.append(dict(
        name='ayu-dark', label='Comfort Ayu Dark', dark=True, gate=True, terminal=True, source='ayu-mirage.json',
        cap=0.12, token_min=5.0, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX,
        bg=bg, fg=h('#CCCAC2'), bold=h('#E6E1CF'), cursor=h('#FFCC66'), sel=blend(h('#409FFF'), bg, 0.25),
        ansi=_ansi({n: tune(v, bg, 0.12, 5.0) for n, v in nor.items()},
                   {n: tune(v, bg, 0.11, 7.0) for n, v in brt.items()},
                   # 官方 black 为近纯黑 #0A0000, 改用 Mirage 的 sunk 面色, 仍够深以保证彩底黑字
                   dict(Black=h('#171B24'), BrightBlack=tune('707A8C', bg, 0.03, 3.4), White=h('#D2D6DC'), BrightWhite=h('#E3E6EA')))))

    # ---- ayu-light: ayu Light, 底由 #FCFCFC 压暗到 #EFF0F2(底亮度 0.87), 字 #5C6166 加深到对比度 7.0 ----
    bg = h('#EFF0F2')
    nor = dict(Red='F07171', Green='86B300', Yellow='EBA400', Blue='22A4E6', Magenta='A37ACC', Cyan='4CBF99')
    T.append(dict(
        name='ayu-light', label='Comfort Ayu Light', dark=False, gate=True, terminal=True, source='ayu-light.json',
        cap=0.14, token_min=4.8, comment_cr=COMMENT_CR,
        bg=bg, fg=h('#4C5158'), bold=h('#33373D'), cursor=h('#F29718'), sel=blend(h('#035BD6'), bg, 0.15),
        ansi=_ansi({n: tune(v, bg, 0.14, 4.8) for n, v in nor.items()},
                   {n: tune(v, bg, 0.14, 6.0, -0.06) for n, v in nor.items()},
                   dict(Black=h('#242936'), BrightBlack=tune('ADAEB1', bg, 0.02, 3.2), White=h('#C9CDD3'), BrightWhite=h('#DFE2E7')))))

    # ---- solarized-dark: 官方 base03 底, 正文比 base1 稍亮, 对比度 7.0 ----
    bg = h('#002B36')
    T.append(dict(
        name='solarized-dark', label='Comfort Solarized Dark', dark=True, gate=True, terminal=True, source='solarized-dark.json',
        cap=0.12, token_min=5.0, comment_cr=COMMENT_CR, syntax_max=SYNTAX_MAX,
        bg=bg, fg=h('#A6B4B4'), bold=h('#EEE8D5'), cursor=h('#93A1A1'), sel=h('#0A4A5A'),
        ansi=_ansi({n: tune(v, bg, 0.12, 5.0) for n, v in SOL_NORMAL.items()},
                   {n: tune(v, bg, 0.11, 6.5, 0.06) for n, v in SOL_BRIGHT.items()},
                   dict(Black=h('#073642'), BrightBlack=tune('657B83', bg, 0.03, 3.4), White=h('#D3CDBB'), BrightWhite=h('#EEE8D5')))))

    # ---- solarized-light: base3 #FDF6E3 压暗为 #F5EEDA, 正文取 base01 与 base02 之间, 对比度 7.0 ----
    bg = h('#F5EEDA')
    T.append(dict(
        name='solarized-light', label='Comfort Solarized Light', dark=False, gate=True, terminal=True, source='solarized-light.json',
        cap=0.12, token_min=4.8, comment_cr=COMMENT_CR,
        bg=bg, fg=h('#3E5259'), bold=h('#073642'), cursor=h('#586E75'), sel=h('#E3D9BC'),
        ansi=_ansi({n: tune(v, bg, 0.12, 4.8) for n, v in SOL_NORMAL.items()},
                   {n: tune(v, bg, 0.12, 6.0, -0.06) for n, v in SOL_BRIGHT.items()},
                   dict(Black=h('#073642'), BrightBlack=tune('93A1A1', bg, 0.03, 3.2), White=h('#DDD5BC'), BrightWhite=h('#EBE4CE')))))
    return T
