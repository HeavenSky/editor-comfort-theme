# 调色流程清单与开关: themes.py(底色, 正文, 终端色)与 gen_vscode.py(语法色, 界面色)里每一步调色都登记在这里, 可逐一开关.
# 用法: uv run tools/steps.py          列出全部步骤, 类别与当前开关
#       COMFORT_STEPS='+neon,-term_floor' uv run tools/gen_vscode.py   临时开 / 关若干步骤生成(逗号分隔, + 开 - 关;
#       也可写 all / none / clear / glare / metric 先整体设为只开该类, 再接逐项调整, 如 'clear,+border_quiet')
#
# 类别:
#   clear  看不清: 对比度不足, 选区 / 高亮看不出, 颜色撞在一起分不开; 默认开
#   glare  刺眼: 过亮, 过艳, 大块亮色; 默认关
#   metric 指标 / 观感: 为门禁分数或统一观感而改原主题颜色(饱和度压缩, 蓝光, 偏色, 极端黑白等); 默认关
# 第一目标是还原原主题色彩: 默认只开 clear 类, 且 clear 类只改读不清的那一侧, 只改到够用.
# 调色链的输入是补全段的中间主题 tools/sources/<name>-full.json(complete.py, 只补缺失不改色); 全关时产物与它逐键相等.
import os, sys

# 名称: (默认开关, 类别, 所在位置, 说明)
STEPS = {
    # ---- 看不清 ----
    'text_floor': (True, 'clear', 'themes.adapt', '正文低于 4.5 时提到 4.5, 色相与饱和度不变'),
    'syntax_floor': (True, 'clear', 'gen_vscode.Mapper.token', '语法色低于 4.5 的提到 4.5, 本来够读的不动'),
    'comment_floor': (True, 'clear', 'gen_vscode.Mapper.token', '注释不低于 3.4, 色相与饱和度不变'),
    'term_floor': (True, 'clear', 'themes.tone', '终端普通色与亮色低于 4.5 时提上来'),
    'term_badge_bw': (False, 'clear', 'themes.adapt', '终端黑 / 亮白比底与正文再深 / 亮一档, 彩色底上的字可读'),
    'term_white_light': (False, 'clear', 'themes.build', '浅色主题的 White 是近黑时改成浅色'),
    'term_separate': (False, 'clear', 'themes.separate_ansi', '终端 6 个普通色两两色差不足时在色槽内转开'),
    'term_gray_floor': (True, 'clear', 'themes.build', '终端 90m 暗灰不低于 3.4'),
    'term_selection': (True, 'clear', 'themes.build', '原终端选区看不出(< 1.3)或上面的字读不清时, 取终端蓝混入底色重算'),
    'ui_text_floor': (True, 'clear', 'gen_vscode.transform', '侧栏, 标签, 状态栏等界面文字不低于 4.5(非活动的 3.0), 行号不低于 2.2; 半透明的先加不透明度'),
    'highlight_text': (True, 'clear', 'gen_vscode.calm', '选区, 查找等高亮底上的正文不低于 3.5'),
    'find_order': (True, 'clear', 'gen_vscode.find_order', '查找当前比其他匹配醒目'),
    'selections': (True, 'clear', 'gen_vscode.selections', '编辑区选区 / 输入框选区看得出, 选中的字可读; 从原选区色出发只动必要的一侧'),
    'list_selection_text': (True, 'clear', 'gen_vscode.list_selection_text', '列表选中 / 聚焦 / 悬停行上的字不低于 4.5(同徽标, 字不换边)'),
    'badge_text': (True, 'clear', 'gen_vscode.quiet_badges', '徽标上的字不低于 4.5: 字不换边, 先推字再微调底色(ΔE <= 15), 不够才换字色'),
    'button_text': (True, 'clear', 'gen_vscode.quiet_buttons', '按钮上的字不低于 4.5: 同徽标, 保留原按钮样式'),
    'ignored_floor': (True, 'clear', 'gen_vscode.quiet_lists_and_borders', '被忽略文件的字低于 3.0 时提上来'),
    'focus_floor': (True, 'clear', 'gen_vscode.quiet_controls', '焦点描边不低于 3.0; 半透明的先加不透明度, 不压彩度'),
    'placeholder_floor': (True, 'clear', 'gen_vscode.quiet_controls', '输入框占位字不低于 2.8'),
    'control_text': (True, 'clear', 'gen_vscode.quiet_controls', '输入框 / 下拉框里的字不低于 4.5'),
    'graph_labels': (True, 'clear', 'gen_vscode.graph_labels', '源代码管理图的分支标签字可读'),
    # ---- 刺眼: 第一目标是还原原主题色彩, 全部默认关(逐项实测见 TODO.md) ----
    'text_cap': (False, 'glare', 'themes.adapt', '正文对比度高于目标时压下来'),
    'syntax_cap': (False, 'glare', 'gen_vscode.Mapper.token', '语法色不亮过 正文 x 1.05(浅色 1.12)'),
    'term_glare_cap': (False, 'glare', 'themes.build', '深色主题终端彩色 / White / 亮白不比正文刺眼, 普通色亮暗跨度封顶'),
    'neon': (False, 'glare', 'themes / gen_vscode', '高明度黄绿到青的荧光感: 先降明度再降彩度'),
    'light_bg': (False, 'glare', 'themes.fit_bg', '浅色编辑区底亮度不超过 0.87(v0.0.1 手调浅色底的水平), 纯白底压暗'),
    'light_panel': (False, 'glare', 'gen_vscode.calm', '浅色主题面板 / 输入框等大面积底亮度不超过 0.86'),
    'panel_glare': (False, 'glare', 'gen_vscode.calm', '面板 / 弹窗 / 列表选中底与编辑区底对比度不超过 1.6'),
    'highlight_cap': (False, 'glare', 'gen_vscode.calm', '选区, 查找等高亮底与编辑区底对比度不超过 2.2'),
    'bright_tint': (False, 'glare', 'gen_vscode.calm', '亮的高亮底(浅色选区, 查找)饱和度不超过 0.40'),
    'area_cap': (False, 'glare', 'gen_vscode.Mapper.ui', '大面积彩色底色 / 边框彩度封顶 0.10'),
    'badge_quiet': (False, 'glare', 'gen_vscode.quiet_badges', '徽标彩度封顶 0.07, 与编辑区底对比度不超过 1.7'),
    'border_quiet': (False, 'glare', 'gen_vscode.quiet_lists_and_borders', '布局边框去彩度, 与编辑区底对比度不超过 1.6'),
    'ui_text_cap': (False, 'glare', 'gen_vscode.quiet_ui_text', '界面文字与图标不比正文更亮(深色)/ 更黑(浅色)'),
    'control_quiet': (False, 'glare', 'gen_vscode.quiet_controls', '输入框描边对比度不超过 2.0, 焦点描边不超过 正文 x 0.8'),
    # ---- 指标 / 观感 ----
    'bg_dark_floor': (False, 'metric', 'themes.fit_bg', '深色底亮度不低于 0.016'),
    'bg_hue': (False, 'metric', 'themes.fit_bg', '浅色底偏暖白, 或按主题色相偏色'),
    'bg_blue': (False, 'metric', 'themes.fit_bg', '浅色底线性蓝光压到 0.70 以内'),
    'syntax_soften': (False, 'metric', 'gen_vscode.Mapper.token', '语法色饱和度平滑压缩(knee 0.80, floor 0.50)'),
    'comment_fit': (False, 'metric', 'gen_vscode.Mapper.token', '注释统一到 正文 / 1.85(3.4~4.2), 饱和度落进 0.12~0.35'),
    'amber': (False, 'metric', 'themes.tone / gen_vscode.Mapper.token', '浅色主题压深的黄朝琥珀转色相'),
    'term_soften': (False, 'metric', 'themes.tone', '终端色饱和度平滑压缩(knee 0.85)'),
    'term_bright_shift': (False, 'metric', 'themes.tone', '终端亮色先整体提亮(深色)/ 压暗(浅色)一档'),
    'term_hue_slot': (False, 'metric', 'themes.vivid', '终端色色相挪回色槽, 饱和度不低于下限'),
    'term_gray_fit': (False, 'metric', 'themes.build', '终端 90m 统一到 正文 / 1.85, 高于 4.2 时压下'),
    'line_no_cap': (False, 'metric', 'gen_vscode.transform', '行号对比度不超过 2.6'),
    'ui_soften': (False, 'metric', 'gen_vscode.Mapper.ui / accent', '界面图标与状态色饱和度平滑压缩(knee 0.70)'),
    'ui_neutral_tint': (False, 'metric', 'gen_vscode.Mapper.ui', '界面中性灰带上底色色调'),
    'panel_chroma': (False, 'metric', 'gen_vscode.calm', '面板底色彩度不超过 0.035'),
    'button_quiet': (False, 'metric', 'gen_vscode.quiet_buttons', '按钮改为低彩度(0.06), 与底对比度 1.75'),
    'list_text_fg': (False, 'metric', 'gen_vscode.quiet_lists_and_borders', '列表选中行的彩色字改用正文色'),
    'placeholder_quiet': (False, 'metric', 'gen_vscode.quiet_controls', '占位字去彩色, 不高于 4.2'),
    'tint_grays': (False, 'metric', 'gen_vscode.tint_grays', '带色调底色上的中间灰块换成底色色调'),
    'unextreme': (False, 'metric', 'themes / gen_vscode.comfortable', '不用纯黑 / 乌黑, 纯白 / 亮白'),
    'ignored_dim': (False, 'metric', 'gen_vscode.quiet_lists_and_borders', '被忽略文件统一到 min(注释, 普通文件 x 0.75), 压彩度'),
}
KINDS = dict(clear='看不清', glare='刺眼', metric='指标 / 观感')


def _resolve() -> dict[str, bool]:
    state = {k: v[0] for k, v in STEPS.items()}
    for item in filter(None, (x.strip() for x in os.environ.get('COMFORT_STEPS', '').split(','))):
        if item in ('all', 'none') or item in KINDS:
            state = {k: item == 'all' or STEPS[k][1] == item for k in STEPS}
            continue
        name, val = (item[1:], item[0] == '+') if item[0] in '+-' else (item, True)
        if name not in STEPS:
            raise SystemExit(f'COMFORT_STEPS: 未知步骤 {name}; 可用: {", ".join(STEPS)}')
        state[name] = val
    return state


STATE = _resolve()


def on(name: str) -> bool:
    return STATE[name]


if __name__ == '__main__':
    for kind, title in KINDS.items():
        print(f'## {title}')
        for k, (default, kd, where, desc) in STEPS.items():
            if kd == kind:
                mark = '开' if STATE[k] else '关'
                note = '' if STATE[k] == default else f' (默认{"开" if default else "关"})'
                print(f'  [{mark}] {k:18} {where:38} {desc}{note}')
    sys.exit(0)
