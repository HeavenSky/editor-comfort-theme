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
    # 列表选中 / 悬停底色(文件树, 问题面板等): 同样是成片的底色, 不应是饱和色条
    'list.activeSelectionBackground', 'list.inactiveSelectionBackground', 'list.focusBackground', 'list.hoverBackground',
    'list.inactiveFocusBackground',
]
PANEL_MAX_CR = 1.6
# 浅色主题的大面积底色(编辑区底与上面的面板)亮度上限: 再亮就像对着白纸灯箱, 久看刺眼; 编辑区底理想 <= LIGHT_BG_MAX
LIGHT_BG_MAX = 0.80
LIGHT_PANEL_MAX = 0.85
# 分隔布局的边框(编辑器拆分线, 侧栏 / 面板 / 标签栏边线): 只需看得出分界, 与编辑区底的对比度不超过上限, 否则一道道线条抢眼
BORDER_KEYS = ['editorGroup.border', 'sideBar.border', 'panel.border', 'tab.border', 'editorGroupHeader.tabsBorder', 'activityBar.border',
               'statusBar.border', 'titleBar.border', 'sideBarSectionHeader.border', 'editorGroupHeader.border', 'panelSection.border',
               'contrastBorder', 'sideBySideEditor.horizontalBorder', 'sideBySideEditor.verticalBorder']
BORDER_MAX_CR = 1.6
# 底色带色调的主题(底色彩度 > TINTED_BG_CHROMA, 如 Sunlit 的青, Owl 的深蓝)里, 大面积底色与悬停 / 选中块不用纯灰:
# 纯灰块(彩度 < GRAY_CHROMA, 多是 VS Code 硬编码默认色补出来的, 如活动栏 / 工具栏选中图标的底)在有色调的底上发灰, 与主题不搭
TINT_KEYS = PANEL_KEYS + ['toolbar.hoverBackground', 'toolbar.activeBackground', 'activityBarTop.activeBackground',
                          'activityBar.activeBackground']
TINTED_BG_CHROMA, GRAY_CHROMA = 0.03, 0.008
# 输入框 / 下拉框等控件(问题面板与输出面板的筛选框, 输出面板的通道下拉框, 设置页等): 描边看得出框即可, 不画亮框;
# 占位提示字(如 Filter (e.g. text, **/...))比输入的字更淡, 落在注释的口径; 输入的字至少 4.5 可读(不超过正文由界面文字规则管);
# 焦点 / 选项激活描边是指示器, 要看得见, 但不比彩色语法更亮
CONTROL_BORDER_KEYS = ['input.border', 'dropdown.border', 'checkbox.border', 'panelInput.border', 'settings.textInputBorder',
                       'settings.dropdownBorder', 'settings.checkboxBorder', 'settings.numberInputBorder']
CONTROL_BORDER_MAX_CR = 2.0
CONTROL_TEXT_PAIRS = [('input.foreground', 'input.background'), ('dropdown.foreground', 'dropdown.background'),
                      ('settings.textInputForeground', 'settings.textInputBackground'),
                      ('settings.dropdownForeground', 'settings.dropdownBackground')]
CONTROL_TEXT_MIN = 4.5
PLACEHOLDER_KEY = 'input.placeholderForeground'
PLACEHOLDER_CR = (2.8, 4.2)
# 占位字与注释一样接近中性: 彩色的提示字(如 Pale Light 的紫)在一排图标间很跳
PLACEHOLDER_MAX_CHROMA = 0.04
FOCUS_KEYS = ['focusBorder', 'inputOption.activeBorder']
# 焦点描边对比度上限 = 正文 x FOCUS_MAX: 指示器比正文略收, 不在屏幕上画一圈亮框
FOCUS_MAX = 0.8
# 焦点描边对比度下限(WCAG 非文本 3:1): 聚焦的输入框必须比未聚焦时更醒目, 不能比 CONTROL_BORDER_MAX_CR 的普通描边还淡
FOCUS_MIN_CR = 3.0
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
# 界面文字与图标(侧边栏, 文件树, 扩展列表, 标签页标题, 活动栏图标, 文件树的 git 着色等)相对其所在底色的对比度
# 不超过 正文 x UI_TEXT_MAX: 这些字常驻视野, 深色主题里比代码还白, 浅色主题里比代码还黑, 都比看代码更累
UI_TEXT_MAX = 1.0
# 不受此限的前景键: 终端色板与光标另有规则, 正文本身是基准
UI_TEXT_SKIP = ('terminal.ansi', 'editorCursor.', 'terminalCursor.', 'editor.foreground', 'terminal.foreground')
# 徽标(活动栏角标, 计数等): 底色与编辑区底的对比度不超过上限, 免得一个个亮块(深色主题)或暗斑(浅色主题)抢眼; 徽标上的字要可读
BADGE_PAIRS = [
    ('activityBarBadge.background', 'activityBarBadge.foreground'), ('badge.background', 'badge.foreground'),
    ('activityErrorBadge.background', 'activityErrorBadge.foreground'),
    ('activityWarningBadge.background', 'activityWarningBadge.foreground'), ('agentsBadge.background', 'agentsBadge.foreground'),
    ('agentsUnreadBadge.background', 'agentsUnreadBadge.foreground'), ('panelTitleBadge.background', 'panelTitleBadge.foreground'),
    ('profileBadge.background', 'profileBadge.foreground'), ('extensionBadge.remoteBackground', 'extensionBadge.remoteForeground'),
    ('testing.coverCountBadgeBackground', 'testing.coverCountBadgeForeground'),
    ('testing.message.error.badgeBackground', 'testing.message.error.badgeForeground'),
]
# 徽标上是一两个粗体数字, 可读口径同高亮底上的字
BADGE_MAX_CR = 2.2
BADGE_TEXT_MIN = HIGHLIGHT_TEXT_MIN

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
    bright_panel=(None, 0, None, 0),         # 浅色主题里亮度 > LIGHT_PANEL_MAX 的大面积底色个数(深色主题不计)
    border=(None, 0, None, 0),               # 与编辑区底对比度 > BORDER_MAX_CR 的布局边框个数
    gray_patch=(None, 0, None, 0),           # 有色调的底上的纯灰底色个数
    control=(None, 0, None, 0),              # 抢眼的控件描边, 过亮或看不见的焦点描边, 过亮或过淡的占位字, 难读的输入字个数
    panel_glare=(None, 0, None, 0),          # 与编辑区底对比度 > 1.6 的面板底色个数
    highlight=(None, 0, None, 0),            # 刺眼(> 2.2)或压字难读(< 4.5)的高亮底色个数
    ui_glare=(None, 0, None, 0),             # 比正文更刺眼的界面文字 / 图标个数
    badge=(None, 0, None, 0),                # 刺眼(> 2.2)或字难读(< 3.5)的徽标个数
)
FATIGUE_LIGHT = dict(FATIGUE_DARK, text=(7.0, 9.0, 6.0, 11.0), bg=(0.65, LIGHT_BG_MAX, 0.55, LIGHT_PANEL_MAX))

NAMES = dict(avg_chroma='平均彩度', max_chroma='最大彩度', span='语法亮度跨度', top_ratio='最亮语法/正文',
             panel_chroma='面板彩度', text='正文', comment='注释', gap='正文/注释', line_no='行号', bg='底亮度',
             panel_glare='面板亮块', highlight='高亮底色', ui_glare='界面文字刺眼', badge='徽标',
             bright_panel='浅色亮底', border='边框抢眼', control='控件', gray_patch='灰块')


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


def border_glare(colors: dict, bg: Rgb) -> list[str]:
    return [k for k in BORDER_KEYS if k in colors and cr(_parse(colors[k], bg), bg) > BORDER_MAX_CR + 0.03]


def control_issues(colors: dict, bg: Rgb, fg: Rgb) -> list[str]:
    out = []
    inp = _parse(colors['input.background'], bg) if 'input.background' in colors else bg
    for k in CONTROL_BORDER_KEYS:
        if k in colors and cr(_parse(colors[k], bg), bg) > CONTROL_BORDER_MAX_CR + 0.03:
            out.append(k)
    for k in FOCUS_KEYS:
        if k in colors and not FOCUS_MIN_CR - 0.03 <= cr(_parse(colors[k], bg), bg) <= cr(fg, bg) * FOCUS_MAX + 0.03:
            out.append(k)
    if PLACEHOLDER_KEY in colors:
        v = cr(_parse(colors[PLACEHOLDER_KEY], inp), inp)
        if not PLACEHOLDER_CR[0] - 0.03 <= v <= PLACEHOLDER_CR[1] + 0.03 or \
                oklch(_parse(colors[PLACEHOLDER_KEY], inp))[1] > PLACEHOLDER_MAX_CHROMA + 0.005:
            out.append(PLACEHOLDER_KEY)
    for fk, bk in CONTROL_TEXT_PAIRS:
        if fk in colors:
            under = _parse(colors[bk], bg) if bk in colors else bg
            if cr(_parse(colors[fk], under), under) < CONTROL_TEXT_MIN - 0.03:
                out.append(fk)
    return out


def gray_patches(colors: dict, bg: Rgb) -> list[str]:
    if oklch(bg)[1] <= TINTED_BG_CHROMA:
        return []
    # 纯黑 / 纯白的半透明叠层只压暗 / 提亮, 色调仍来自底色, 不算; 中间灰(L 0.12~0.92)且占比 >= 20% 才会把底色冲成灰
    out = []
    for k in TINT_KEYS:
        if k not in colors:
            continue
        v = colors[k].lstrip('#')
        L, C, _ = oklch(h(v[:6]))
        a = int(v[6:8], 16) / 255 if len(v) == 8 else 1.0
        if C < GRAY_CHROMA and 0.12 < L < 0.92 and a >= 0.2:
            out.append(k)
    return out


def bright_panels(colors: dict, bg: Rgb) -> list[str]:
    # 编辑区底本身由 bg 子指标管; 这里看压在视野里的其他大面积底色(侧栏, 面板, 输入框, 标签栏等)
    return [k for k in PANEL_KEYS if k in colors and lum(_parse(colors[k], bg)) > LIGHT_PANEL_MAX + 0.005]


def own_background(colors: dict, key: str, bg: Rgb) -> tuple[Rgb, bool]:
    """前景键所在的底色: 同名的 *background 键(如 tab.activeForeground -> tab.activeBackground), 没有时为编辑区底.
    第二项为该底色是否是彩色小块(与编辑区底对比度超过面板上限, 如按钮, 徽标), 这类底上的字按各自规则另算."""
    k = key[:-10] + ('Background' if key[-10] == 'F' else 'background')
    if k not in colors:
        return bg, False
    under = _parse(colors[k], bg)
    return under, cr(under, bg) > PANEL_MAX_CR


def ui_text_glare(colors: dict, bg: Rgb, fg: Rgb) -> list[str]:
    limit = cr(fg, bg) * UI_TEXT_MAX + 0.05
    out = []
    for k, v in colors.items():
        if not k.lower().endswith('foreground') or k.startswith(UI_TEXT_SKIP):
            continue
        under, colored = own_background(colors, k, bg)
        if not colored and cr(_parse(v, under), under) > limit:
            out.append(k)
    return out


def badge_issues(colors: dict, bg: Rgb, dark: bool) -> list[str]:
    out = []
    for bk, fk in BADGE_PAIRS:
        if bk not in colors:
            continue
        under = _parse(colors[bk], bg)
        text = _parse(colors[fk], under) if fk in colors else None
        if cr(under, bg) > BADGE_MAX_CR + 0.03 or (text is not None and cr(text, under) < BADGE_TEXT_MIN - 0.03):
            out.append(bk)
    return out


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
    glare = bad = ui = badges = borders = bright = controls = grays = []
    colors = m.get('colors')
    if colors:
        soft_v['panel_chroma'] = max((oklch(_parse(colors[k], bg))[1] for k in PANEL_KEYS if k in colors), default=0.0)
        glare, bad = _patches(colors, bg, m['fg'])
        ui, badges = ui_text_glare(colors, bg, m['fg']), badge_issues(colors, bg, dark)
        borders, bright = border_glare(colors, bg), ([] if dark else bright_panels(colors, bg))
        controls = control_issues(colors, bg, m['fg'])
        grays = gray_patches(colors, bg)
        fat_v.update(panel_glare=len(glare), highlight=len(bad), ui_glare=len(ui), badge=len(badges), border=len(borders),
                     bright_panel=len(bright), control=len(controls), gray_patch=len(grays))
    soft = _rate(soft_v, SOFT)
    fatigue = _rate(fat_v, FATIGUE_DARK if dark else FATIGUE_LIGHT)
    if glare:
        fatigue['why'].append('面板亮块: ' + ', '.join(glare))
    if bad:
        fatigue['why'].append('高亮底色: ' + ', '.join(bad))
    if ui:
        fatigue['why'].append('界面文字刺眼: ' + ', '.join(ui))
    if badges:
        fatigue['why'].append('徽标: ' + ', '.join(badges))
    if colors and borders:
        fatigue['why'].append('边框抢眼: ' + ', '.join(borders))
    if colors and grays:
        fatigue['why'].append('灰块: ' + ', '.join(grays))
    if colors and controls:
        fatigue['why'].append('控件: ' + ', '.join(controls))
    if colors and bright:
        fatigue['why'].append('浅色亮底: ' + ', '.join(bright))
    return dict(soft=soft, fatigue=fatigue)
