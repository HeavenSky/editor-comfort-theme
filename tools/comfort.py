# 柔和安静 / 护眼防疲劳 两条门禁规则的打分; metrics.py 与 similar.py 共用.
#
# 每个子指标给出 理想区间 与 限值区间: 落在理想区间得 100, 到限值线性降到 60, 越过限值继续线性降到 0 并判失败.
# 一条规则的得分为其子指标得分的平均; 规则通过 = 没有子指标越过限值. 指标取不到(例如 .terminal 没有注释色)时跳过.
from colorlib import Rgb, blend, cr, h, lum, oklch

# 画大面积的面板 / 弹窗底色: 与编辑区底的对比度超过上限即为视野里的亮块(深色主题)或暗块(浅色主题)
PANEL_KEYS = [
    'editorWidget.background', 'editorHoverWidget.background', 'editorSuggestWidget.background', 'notifications.background',
    'peekViewEditor.background', 'peekViewResult.background', 'peekViewTitle.background', 'debugExceptionWidget.background',
    'menu.background', 'quickInput.background', 'panel.background', 'sideBar.background', 'sideBarSectionHeader.background',
    'activityBar.background', 'statusBar.background', 'titleBar.activeBackground', 'tab.activeBackground', 'tab.inactiveBackground',
    'editorGroupHeader.tabsBackground', 'input.background', 'dropdown.background', 'terminal.background',
    'inputValidation.infoBackground', 'inputValidation.warningBackground', 'inputValidation.errorBackground',
    'mergeEditor.changeBase.background', 'list.dropBackground', 'editor.lineHighlightBackground', 'editorGutter.background',
    'minimap.background',
]
PANEL_MAX_CR = 1.6
PANEL_MAX_CHROMA = 0.03     # 面板底色的理想最大彩度: 大面积底色应接近中性
# 画在代码文字下面的高亮底色: 既不能刺眼, 也要让压在上面的正文仍然好读
HIGHLIGHT_KEYS = [
    'editor.selectionBackground', 'editor.findMatchBackground', 'editor.findMatchHighlightBackground',
    'editor.hoverHighlightBackground', 'editor.wordHighlightBackground', 'editor.wordHighlightStrongBackground',
    'editor.selectionHighlightBackground', 'peekViewEditor.matchHighlightBackground', 'peekViewResult.matchHighlightBackground',
    'editor.rangeHighlightBackground', 'editorBracketMatch.background', 'mergeEditor.changeBase.word.background',
    'diffEditor.insertedTextBackground', 'diffEditor.removedTextBackground',
]
HIGHLIGHT_MAX_CR = 2.2
HIGHLIGHT_TEXT_MIN = 3.5

# 彩度低于它的语法色视为中性(与正文同色的标点, 运算符等), 不计入亮度跨度
NEUTRAL_CHROMA = 0.035

# (理想下限, 理想上限, 限值下限, 限值上限); None 表示该侧不设限
SOFT = dict(
    avg_chroma=(None, 0.07, None, 0.10),     # 语法色平均彩度: 整屏的鲜艳程度
    max_chroma=(None, 0.10, None, 0.14),     # 最鲜艳的一个颜色(语法, 括号, 终端)
    span=(None, 1.40, None, 1.75),           # 彩色语法色里最亮 / 最暗的对比度之比: 越大字面越"跳"
    top_ratio=(None, 1.00, None, 1.10),      # 最亮语法色 / 正文: 彩色不应比正文更抢眼
    panel_chroma=(None, PANEL_MAX_CHROMA, None, 0.06),  # 面板底色的最大彩度: 大面积底色应接近中性
)
FATIGUE_DARK = dict(
    text=(6.0, 7.5, 5.0, 8.5),               # 正文对比度: 太低吃力, 太高在暗底上发光(光晕)
    comment=(3.4, 4.2, 3.0, 4.8),            # 注释对比度: 斜体细字, 太淡要眯眼; 目标 正文 / 1.85
    gap=(None, 1.9, None, 2.3),              # 正文 / 注释: 两者落差过大时视线反复调焦
    line_no=(2.0, 2.6, 1.8, 3.0),            # 行号对比度: 常驻视野边缘, 够读即可
    bg=(0.015, 0.035, 0.010, 0.050),         # 底亮度: 近纯黑时字的光晕重
    panel_glare=(None, 0, None, 0),          # 与编辑区底对比度 > 1.6 的面板底色个数
    highlight=(None, 0, None, 0),            # 刺眼(> 2.2)或压字难读(< 4.5)的高亮底色个数
)
FATIGUE_LIGHT = dict(FATIGUE_DARK, text=(7.0, 9.0, 6.0, 11.0), bg=(0.70, 0.85, 0.60, 0.90))

NAMES = dict(avg_chroma='平均彩度', max_chroma='最大彩度', span='语法亮度跨度', top_ratio='最亮语法/正文',
             panel_chroma='面板彩度', text='正文', comment='注释', gap='正文/注释', line_no='行号', bg='底亮度',
             panel_glare='面板亮块', highlight='高亮底色')


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


def _patches(colors: dict, bg: Rgb, fg: Rgb) -> tuple[list[str], list[str]]:
    glare = [k for k in PANEL_KEYS if k in colors and cr(_parse(colors[k], bg), bg) > PANEL_MAX_CR]
    bad = []
    for k in HIGHLIGHT_KEYS:
        if k not in colors:
            continue
        under = _parse(colors[k], bg)
        if cr(under, bg) > HIGHLIGHT_MAX_CR or cr(fg, under) < HIGHLIGHT_TEXT_MIN:
            bad.append(k)
    return glare, bad


def rate(m: dict) -> dict:
    """m 为 metrics.from_vscode / from_terminal 的结果; 返回 soft 与 fatigue 两条规则的评分."""
    bg, dark = m['bg'], lum(m['bg']) < 0.2
    syn = m.get('syn_colors') or []
    soft_v = dict(max_chroma=max(m['chroma']) if m.get('chroma') else None)
    if syn:
        crs = [cr(c, bg) for c in syn]
        soft_v.update(avg_chroma=sum(oklch(c)[1] for c in syn) / len(syn), top_ratio=max(crs) / m['text'])
        colored = [cr(c, bg) for c in syn if oklch(c)[1] > NEUTRAL_CHROMA]
        if colored:
            soft_v['span'] = max(colored) / min(colored)
    # 注释看 `comment` 主规则(注释正文)的颜色; 注释符号等更淡的子规则不影响阅读
    comment = m.get('comment_main') or m.get('comment')
    fat_v = dict(text=m['text'], comment=comment, line_no=m.get('line_no'), bg=lum(bg))
    if comment:
        fat_v['gap'] = m['text'] / comment
    glare = bad = []
    colors = m.get('colors')
    if colors:
        soft_v['panel_chroma'] = max((oklch(_parse(colors[k], bg))[1] for k in PANEL_KEYS if k in colors), default=0.0)
        glare, bad = _patches(colors, bg, m['fg'])
        fat_v.update(panel_glare=len(glare), highlight=len(bad))
    soft = _rate(soft_v, SOFT)
    fatigue = _rate(fat_v, FATIGUE_DARK if dark else FATIGUE_LIGHT)
    if glare:
        fatigue['why'].append('面板亮块: ' + ', '.join(glare))
    if bad:
        fatigue['why'].append('高亮底色: ' + ', '.join(bad))
    return dict(soft=soft, fatigue=fatigue)
