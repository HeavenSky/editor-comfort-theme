# 门禁打分: 范围(终端 / 编辑区 / 界面) x 维度(清晰 / 鲜艳柔和 / 防疲劳 / 护眼 / 防蓝光); metrics.py 与 similar.py 共用,
# 顶部的界面常量与检查函数也是 gen_vscode.py 的调色口径.
#
# 每个子指标给出 理想区间 与 限值区间: 落在理想区间得 100, 到限值线性降到 60, 越过限值继续线性降到 0 并判失败.
# 一格(维度 x 范围)的得分为其子指标得分的平均; 通过 = 没有子指标越过限值. 指标取不到(例如 .terminal 没有编辑区)时跳过.
import math

from colorlib import Rgb, blend, blue_light, cr, de2000, h, lum, neon, oklch, sat

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
LIGHT_BG_MAX = 0.82
LIGHT_PANEL_MAX = 0.86
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
PANEL_MAX_CHROMA = 0.035    # 面板底色的理想最大彩度: 大面积底色带底色的色调, 但不成彩色块
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
# 亮的高亮底(OKLCH 明度 > BRIGHT_TINT_L)饱和度: (理想上限, 限值); 近白处可达彩度很小, 同样的彩度已是糖果色(如 #FFAFAF 饱和度 1.0),
# 大面积底色要安静; 暗色块的饱和度不刺眼, 不限. Claude Code 主题的背景块用同一口径
BRIGHT_TINT_L, BRIGHT_TINT_SAT = 0.6, (0.40, 0.55)
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

# 选中文字的底: 编辑区选区(editor.selectionBackground, 叠在编辑区底上)与输入框里选中文字的底(selection.background, 叠在输入框底上,
# 如搜索框, 筛选框). 要看得出选中了, 压在上面的字仍可读, 也不成刺眼色块; selection.background 不定义时由系统高亮色决定, 一律要求定义
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


# ======== 门禁: 范围 x 维度 ========
# 范围: 终端 / 编辑区 / 界面(其余位置: 侧栏, 标签栏, 状态栏, 面板, 弹窗, 徽标, 控件). 综合分按 SCOPE_WEIGHTS 加权.
# 维度: 清晰(读得清, 分得开) / 鲜艳柔和(不灰也不刺眼, 用饱和度而不是绝对彩度衡量) / 防疲劳(对比关系) /
#       护眼(绝对亮度: 底亮度, 极端黑白, 浅色亮底) / 防蓝光(按面积加权的蓝光发光量).
# 每格(维度 x 范围)= 子指标得分平均; 范围分 = 各维度平均; 维度分 = 各范围按 SCOPE_WEIGHTS 加权; 任一子指标越限即不通过.
SCOPES = ['term', 'editor', 'ui']
SCOPE_NAMES = dict(term='终端', editor='编辑区', ui='界面')
SCOPE_WEIGHTS = dict(term=2, editor=2, ui=1)
DIMS = ['clear', 'vivid', 'fatigue', 'eye', 'blue']
DIM_NAMES = dict(clear='清晰', vivid='鲜艳柔和', fatigue='防疲劳', eye='护眼', blue='防蓝光')

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
# 界面的大面积表面与常驻文字: 防蓝光按它们算发光量
UI_SURFACES = ['sideBar.background', 'activityBar.background', 'statusBar.background', 'tab.inactiveBackground',
               'editorGroupHeader.tabsBackground', 'panel.background', 'titleBar.activeBackground']
UI_TEXTS = ['sideBar.foreground', 'foreground', 'tab.activeForeground', 'statusBar.foreground']
# 编辑区范围的颜色键前缀(极端黑白按范围计数); 终端为 terminal 前缀, 其余归界面
EDITOR_PREFIXES = ('editor', 'diffEditor', 'minimap', 'merge')
# 极端黑白: 不透明色(透明度 >= 0.9)亮度低于 / 高于它即为纯黑 / 乌黑, 纯白 / 亮白; 阴影类键(半透明遮罩)不计
EXTREME_DARK, EXTREME_LIGHT = 0.008, 0.88
# 面积权重(防蓝光): 底占视野大头, 文字只占一小部分
BLUE_AREA = dict(bg=0.85, text=0.15)
# 饱和蓝的大面积底(状态栏, 选中行等): 色相范围, 饱和度与亮度下限
BLUE_HUE, BLUE_PANEL_SAT, BLUE_PANEL_LUM = (230, 290), 0.5, 0.2
# 荧光度(colorlib.neon)上限: 理想 / 限值; 终端彩色(也会被当底色用, 如 42m 与 Claude Code ansi 主题的 diff), 语法色, 界面状态色与高亮底色都看
NEON_SPEC = (None, 0.05, None, 0.075)


def specs(dark: bool) -> dict:
    """(理想下限, 理想上限, 限值下限, 限值上限); None 表示该侧不设限. 返回 {维度: {范围: {子指标: spec}}}.
    饱和度区间按原主题校准: 编辑区平均饱和度原主题 0.64~0.94(多数 0.85 以上), 终端 0.66~0.93; 角色色差原主题多在 12 以上."""
    zero = (None, 0, None, 0)
    text_hi = (None, 7.5, None, 8.5) if dark else (None, 9.0, None, 11.0)
    bg = (0.015, 0.035, 0.010, 0.050) if dark else (0.70, LIGHT_BG_MAX, 0.60, LIGHT_PANEL_MAX)
    blue = dict(dose=(None, 0.68, None, 0.80), **({} if dark else dict(ratio=(None, 1.00, None, 1.15))))
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
                    input_selection_text=(INPUT_SELECTION_TEXT[0], None, INPUT_SELECTION_TEXT[1], None))),
        vivid=dict(
            term=dict(sat=(0.62, 0.88, 0.45, 0.95), sat_min=(0.50, None, 0.38, None), accent_span=(None, 1.6, None, 2.0),
                      neon=NEON_SPEC, bright_tint=(None, BRIGHT_TINT_SAT[0], None, BRIGHT_TINT_SAT[1]),
                      **(dict(glare=(None, 1.2, None, 1.35)) if dark else {})),
            editor=dict(sat=(0.65, 0.88, 0.50, 0.95), sat_min=(0.50, None, 0.38, None), span=(1.15, 1.60, 1.05, 1.90),
                        neon=NEON_SPEC, bright_tint=(None, BRIGHT_TINT_SAT[0], None, BRIGHT_TINT_SAT[1]),
                        **(dict(top_ratio=(None, 1.05, None, 1.15)) if dark else {})),
            ui=dict(sat=(0.55, 0.88, 0.40, 0.95), neon=NEON_SPEC, panel_chroma=(None, PANEL_MAX_CHROMA, None, 0.06), gray_patch=zero,
                    badge_glare=(None, BADGE_MAX_CR, None, 2.6))),
        fatigue=dict(
            term=dict(text_hi=text_hi, gray_hi=(None, 4.2, None, 4.8)),
            editor=dict(text_hi=text_hi, comment_hi=(None, 4.2, None, 4.8), gap=(None, 1.9, None, 2.3),
                        line_no_hi=(None, 2.6, None, 3.0), highlight=(None, HIGHLIGHT_MAX_CR, None, 2.6)),
            ui=dict(panel_glare=zero, border=zero, control=zero, ui_glare=zero,
                    input_selection_glare=(None, HIGHLIGHT_MAX_CR, None, 2.6))),
        eye=dict(
            term=dict(bg=bg, extreme=zero),
            editor=dict(bg=bg, extreme=zero),
            ui=dict(extreme=zero, **({} if dark else dict(bright_panel=zero)))),
        blue=dict(term=dict(blue), editor=dict(blue), ui=dict(blue, blue_panel=zero)),
    )


def term_spec(dark: bool) -> dict:
    """终端范围各维度的子指标合成一张表 {子指标: spec}: 终端色(.terminal, VS Code 的 terminal.*, Claude Code 主题)
    生成时只按它取目标, 不借用编辑区 / 界面的口径."""
    sp = specs(dark)
    return {k: v for dim in DIMS for k, v in sp[dim]['term'].items()}


NAMES = dict(text='正文', accent='彩字', bright='亮色', badge='徽标字', gray='90m', distinct='最近色差', hue_slot='串色',
             selection='选区', inactive_selection='失焦选区', on_selection='选区上的字',
             selection_visible='编辑区选区', input_selection='输入框选区', input_selection_text='输入框选中的字',
             input_selection_glare='输入框选区刺眼', syntax='语法下限', comment='注释', line_no='行号', roles='角色色差', on_highlight='高亮上的字',
             ui_text='界面文字', small_text='小块上的字', focus='焦点描边', status='状态色差',
             sat='平均饱和度', sat_min='最灰饱和度', accent_span='彩字跨度', glare='最亮彩字/正文', span='语法跨度',
             top_ratio='最亮语法/正文', panel_chroma='面板彩度', gray_patch='灰块', badge_glare='徽标亮块', bright_tint='亮底饱和度',
             text_hi='正文上限', gray_hi='90m上限', comment_hi='注释上限', gap='正文/注释', line_no_hi='行号上限',
             highlight='高亮底', panel_glare='面板亮块', border='边框抢眼', control='控件抢眼', ui_glare='界面文字刺眼',
             bg='底亮度', extreme='极端黑白', bright_panel='浅色亮底', dose='蓝光量', ratio='蓝光比', blue_panel='饱和蓝底', neon='荧光度')



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



def _in_hue(deg: float, rng: tuple) -> bool:
    lo, hi = rng
    return lo <= deg <= hi if lo <= hi else deg >= lo or deg <= hi


def _deg(c: Rgb) -> float:
    return math.degrees(oklch(c)[2]) % 360


def _opaque(colors: dict, keys, bg: Rgb) -> list[Rgb]:
    return [_parse(colors[k], bg) for k in keys if k in colors]


def extremes(colors: dict, keys) -> list[str]:
    """不透明(透明度 >= 0.9)且亮度在 EXTREME_DARK / EXTREME_LIGHT 之外的颜色键; 阴影类键不计."""
    out = []
    for k in keys:
        v = colors.get(k)
        if not isinstance(v, str) or 'shadow' in k.lower():
            continue
        s = v.lstrip('#')
        s = ''.join(ch * 2 for ch in s) if len(s) in (3, 4) else s
        if len(s) == 8 and int(s[6:8], 16) / 255 < 0.9:
            continue
        y = lum(h(s[:6]))
        if y < EXTREME_DARK or y > EXTREME_LIGHT:
            out.append(k)
    return out


def blue_dose(bgs: list[Rgb], texts: list[Rgb]) -> tuple[float, float]:
    """按面积加权的(蓝光量, 蓝光比): 底 BLUE_AREA['bg'], 文字 BLUE_AREA['text']; 蓝光比 = 蓝光量 / 同权重亮度, 中性白为 1."""
    avg = lambda f, cs: sum(map(f, cs)) / len(cs) if cs else 0.0
    wb, wt = BLUE_AREA['bg'], BLUE_AREA['text'] if texts else 0.0
    dose = wb * avg(blue_light, bgs) + wt * avg(blue_light, texts)
    y = wb * avg(lum, bgs) + wt * avg(lum, texts)
    return dose, dose / y if y > 1e-6 else 1.0


def _min_de(cs: list[Rgb]) -> float | None:
    pairs = [de2000(a, b) for i, a in enumerate(cs) for b in cs[i + 1:]]
    return min(pairs) if pairs else None


def term_values(pal: list[Rgb], bg: Rgb, fg: Rgb, sel: Rgb | None = None, sel_inactive: Rgb | None = None) -> dict:
    """终端范围: pal 为 16 色(Black, Red, ..., White, BrightBlack, ...), bg / fg 为终端底色与正文,
    sel / sel_inactive 为叠到终端底上的选区 / 失焦选区(取不到时不计)."""
    sels = [c for c in (sel, sel_inactive) if c is not None]
    bright_sels = [sat(c) for c in sels if oklch(c)[0] > BRIGHT_TINT_L]
    normal, bright = pal[1:7], pal[9:15]
    colored = normal + bright
    names = TERM_COLORS + TERM_COLORS
    text = cr(fg, bg)
    crs = [cr(c, bg) for c in normal]
    sats = [sat(c) for c in colored]
    # 文字部分: 正文占 2/3, 彩字占 1/3
    dose_t = BLUE_AREA['bg'] * blue_light(bg) + BLUE_AREA['text'] * (2 * blue_light(fg) + sum(map(blue_light, colored)) / 12) / 3
    y_t = BLUE_AREA['bg'] * lum(bg) + BLUE_AREA['text'] * (2 * lum(fg) + sum(map(lum, colored)) / 12) / 3
    return dict(
        clear=dict(text=text, accent=min(crs), bright=min(cr(c, bg) for c in bright),
                   badge=min(max(cr(pal[0], c), cr(pal[15], c), cr(pal[7], c)) for c in colored),
                   gray=cr(pal[8], bg), distinct=_min_de(normal),
                   hue_slot=sum(not _in_hue(_deg(c), TERM_HUES[n]) for n, c in zip(names, colored)),
                   selection=cr(sel, bg) if sel else None, inactive_selection=cr(sel_inactive, bg) if sel_inactive else None,
                   on_selection=cr(fg, sel) if sel else None),
        vivid=dict(sat=sum(sats) / len(sats), sat_min=min(sats), accent_span=max(crs) / min(crs), neon=max(map(neon, colored + sels)),
                   bright_tint=max(bright_sels, default=None),
                   glare=max(cr(c, bg) for c in colored) / text),
        fatigue=dict(text_hi=text, gray_hi=cr(pal[8], bg)),
        eye=dict(bg=lum(bg), extreme=sum(lum(c) < EXTREME_DARK or lum(c) > EXTREME_LIGHT for c in pal + [bg, fg])),
        blue=dict(dose=dose_t, ratio=dose_t / y_t if y_t > 1e-6 else 1.0),
    )


def editor_values(m: dict) -> dict:
    import pool
    bg, fg, colors, text = m['bg'], m['fg'], m['colors'], m['text']
    syn = m.get('syn_colors') or []
    colored = [c for c in syn if oklch(c)[1] > NEUTRAL_CHROMA]
    ccrs = [cr(c, bg) for c in colored]
    fghex = '#%02X%02X%02X' % tuple(round(v * 255) for v in fg)
    roles = [pool._rgb(pool.role_value(m.get('rules') or [], r, fghex)) for r in MAIN_ROLES]
    roles = [_parse('#%02X%02X%02X' % tuple(round(v * 255) for v in c), bg) for c in roles if c]
    croles = [c for c in roles if oklch(c)[1] > NEUTRAL_CHROMA]
    under = _opaque(colors, HIGHLIGHT_KEYS, bg)
    comment = m.get('comment_main') or m.get('comment')
    # 文字部分: 正文与语法色各占一半
    wt = BLUE_AREA['text'] / 2
    mean = lambda f: sum(map(f, syn)) / len(syn) if syn else f(fg)
    dose = BLUE_AREA['bg'] * blue_light(bg) + wt * (blue_light(fg) + mean(blue_light))
    y = BLUE_AREA['bg'] * lum(bg) + wt * (lum(fg) + mean(lum))
    ratio = dose / y if y > 1e-6 else 1.0
    keys = [k for k in colors if k.startswith(EDITOR_PREFIXES)]
    return dict(
        clear=dict(text=text, syntax=min(cr(c, bg) for c in syn) if syn else None, comment=comment, line_no=m.get('line_no'),
                   roles=_min_de(croles), on_highlight=min((cr(fg, u) for u in under), default=None),
                   selection_visible=cr(_parse(colors['editor.selectionBackground'], bg), bg) if 'editor.selectionBackground' in colors else 1.0),
        vivid=dict(sat=sum(map(sat, colored)) / len(colored) if colored else None, sat_min=min(map(sat, croles), default=None),
                   span=max(ccrs) / min(ccrs) if ccrs else None, top_ratio=max(cr(c, bg) for c in syn) / text if syn else None,
                   neon=max(map(neon, syn + under), default=0.0),
                   bright_tint=max((sat(u) for u in under if oklch(u)[0] > BRIGHT_TINT_L), default=0.0)),
        fatigue=dict(text_hi=text, comment_hi=comment, gap=text / comment if comment else None, line_no_hi=m.get('line_no'),
                     highlight=max((cr(u, bg) for u in under), default=None)),
        eye=dict(bg=lum(bg), extreme=len(extremes(colors, keys)) + sum(lum(c) < EXTREME_DARK or lum(c) > EXTREME_LIGHT for c in syn)),
        blue=dict(dose=dose, ratio=ratio),
    ), dict(extreme=extremes(colors, keys))


def ui_values(m: dict) -> tuple[dict, dict]:
    bg, fg, colors = m['bg'], m['fg'], m['colors']
    dark = lum(bg) < 0.2
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
    accents = [c for c in _opaque(colors, [k for g in STATUS_GROUPS for k in g], bg) if oklch(c)[1] > NEUTRAL_CHROMA]
    glare, _ = _patches(colors, bg, fg)
    surfaces = _opaque(colors, UI_SURFACES, bg) or [bg]
    texts = _opaque(colors, UI_TEXTS, bg)
    dose, ratio = blue_dose(surfaces, texts)
    bluish = []
    for k in PANEL_KEYS + ['statusBar.background', 'list.activeSelectionBackground']:
        if k in colors:
            c = _parse(colors[k], bg)
            if _in_hue(_deg(c), BLUE_HUE) and sat(c) > BLUE_PANEL_SAT and lum(c) > BLUE_PANEL_LUM:
                bluish.append(k)
    keys = [k for k in colors if not k.startswith(EDITOR_PREFIXES) and not k.startswith('terminal')]
    inp, isel, itext = input_selection(colors, bg)
    issues = dict(panel_glare=glare, border=border_glare(colors, bg), control=control_glare(colors, bg, fg),
                  ui_glare=ui_text_glare(colors, bg, fg), gray_patch=gray_patches(colors, bg),
                  bright_panel=[] if dark else bright_panels(colors, bg), extreme=extremes(colors, keys), blue_panel=bluish)
    return dict(
        clear=dict(ui_text=m.get('ui'), small_text=min(small, default=None),
                   focus=min((cr(c, bg) for c in _opaque(colors, FOCUS_KEYS, bg)), default=None), status=min(status, default=None),
                   # 未定义 selection.background 按看不见计(由系统高亮色决定, 不可控)
                   input_selection=cr(isel, inp) if isel else 1.0, input_selection_text=cr(itext, isel) if isel else None),
        vivid=dict(sat=sum(map(sat, accents)) / len(accents) if accents else None,
                   neon=max(map(neon, accents + _opaque(colors, PANEL_KEYS + ['statusBar.background'], bg)), default=0.0),
                   panel_chroma=max((oklch(_parse(colors[k], bg))[1] for k in PANEL_KEYS if k in colors), default=0.0),
                   gray_patch=len(issues['gray_patch']),
                   badge_glare=max((cr(c, bg) for c in _opaque(colors, [b for b, _ in BADGE_PAIRS] + ['button.background'], bg)), default=None)),
        fatigue=dict(panel_glare=len(glare), border=len(issues['border']), control=len(issues['control']), ui_glare=len(issues['ui_glare']),
                     input_selection_glare=cr(isel, inp) if isel else None),
        eye=dict(extreme=len(issues['extreme']), bright_panel=len(issues['bright_panel'])),
        blue=dict(dose=dose, ratio=ratio, blue_panel=len(bluish)),
    ), issues


def control_glare(colors: dict, bg: Rgb, fg: Rgb) -> list[str]:
    """控件里抢眼的部分: 描边过亮, 焦点描边超过 正文 x FOCUS_MAX, 占位字过亮或带彩色; 太淡的一侧归清晰维度."""
    out = [k for k in CONTROL_BORDER_KEYS if k in colors and cr(_parse(colors[k], bg), bg) > CONTROL_BORDER_MAX_CR + 0.03]
    out += [k for k in FOCUS_KEYS if k in colors and cr(_parse(colors[k], bg), bg) > cr(fg, bg) * FOCUS_MAX + 0.03]
    if PLACEHOLDER_KEY in colors:
        inp = _parse(colors['input.background'], bg) if 'input.background' in colors else bg
        ph = _parse(colors[PLACEHOLDER_KEY], inp)
        if cr(ph, inp) > PLACEHOLDER_CR[1] + 0.03 or oklch(ph)[1] > PLACEHOLDER_MAX_CHROMA + 0.005:
            out.append(PLACEHOLDER_KEY)
    return out


def _avg(items: list[tuple[float, float]]) -> float | None:
    w = sum(x for x, _ in items)
    return round(sum(x * s for x, s in items) / w) if w else None


def rate(m: dict) -> dict:
    """m 为 metrics.from_vscode / from_terminal 的结果. 返回
    cells {(维度, 范围): {score, ok, why, subs}}, scope {范围: {score, ok}}, dim {维度: {score, ok}}, overall {score, ok}, issues, diag."""
    dark = lum(m['bg']) < 0.2
    sp = specs(dark)
    values, issues = {}, {}
    if m.get('pal'):
        values['term'] = term_values(m['pal'], m['term_bg'], m['term_fg'], m.get('term_sel'), m.get('term_sel_inactive'))
    if m.get('colors') is not None:
        values['editor'], issues['editor'] = editor_values(m)
        values['ui'], issues['ui'] = ui_values(m)
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
    return dict(cells=cells, scope=scope, dim=dim, overall=overall, issues=issues, diag=diag)
