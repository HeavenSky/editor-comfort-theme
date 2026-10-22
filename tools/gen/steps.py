# 调色流程清单与开关: themes.py(底色, 正文, 终端色)与 gen_vscode.py(语法色, 界面色)里每一步调色都登记在这里, 可逐一开关.
# 用法: uv run tools/gen/steps.py          列出全部步骤, 类别与当前开关
#       COMFORT_STEPS='+neon,-term_floor' uv run tools/gen/gen_vscode.py   临时开 / 关若干步骤生成(逗号分隔, + 开 - 关;
#       也可写 all / none / clear / glare 先整体设为只开该类, 再接逐项调整, 如 'clear,-find_order')
#
# 类别:
#   clear  看不清: 对比度不足, 选区 / 高亮看不出, 颜色撞在一起分不开
#   glare  刺眼: 只有深色主题的近纯白(用户定)
# 第一目标是还原原主题色彩: 只改读不清的那一侧, 只改到够用; 压彩度, 压亮度, 统一观感这类改原主题观感的步骤已删除.
# 调色链的输入是补全段的中间主题 assets/full-theme/<name>-full.json(complete.py, 只补缺失不改色); 全关时产物与它逐键相等.
import os, sys

# 名称: (默认开关, 类别, 所在位置, 说明)
STEPS = {
    # ---- 看不清 ----
    'text_floor': (True, 'clear', 'themes.adapt', '正文低于 4.5 时提到 4.5, 色相与饱和度不变'),
    'level_floor': (True, 'clear', 'gen_vscode.transform / levels.fix', '界面颜色按分层门槛(assets/levels.json)提到修复下限: 半透明先加不透明度, 再只调明度; 字必须翻到底色另一侧时取本主题的编辑区底 / 正文; 界面文字, 徽标 / 按钮 / 列表选中行上的字, 焦点描边, 占位字等都归它'),
    'syntax_floor': (True, 'clear', 'gen_vscode.Mapper.token', '语法色低于 4.5 的提到 4.5, 本来够读的不动'),
    'comment_floor': (True, 'clear', 'gen_vscode.Mapper.token', '注释不低于 3.4, 色相与饱和度不变'),
    'syntax_separate': (True, 'clear', 'gen_vscode.transform / separate.fix', '案例集里要分开(assets/layers/roles.json)却撞色的语法角色换成主题自有颜色(原语法彩色 + 终端 6 色), 先动次要角色, 目标色相取层次更好的姊妹主题; 降到前 5 名参照主题的中位撞色数即停; 例外: 主要角色之间必须分开的对(如字符串与类型)达线后仍拆, 只动 token 少的一方'),
    'term_floor': (True, 'clear', 'themes.tone', '终端普通色与亮色低于 4.5 时提上来'),
    'term_gray_floor': (True, 'clear', 'themes.build', '终端 90m 暗灰不低于 3.4'),
    'term_selection': (True, 'clear', 'themes.build', '原终端选区看不出(< 1.3)或上面的字读不清时, 取终端蓝混入底色重算'),
    'highlight_text': (True, 'clear', 'gen_vscode.highlight_text_floor', '选区, 查找等高亮底上的正文不低于 3.5'),
    'find_order': (True, 'clear', 'gen_vscode.find_order', '查找当前比其他匹配醒目'),
    'selections': (True, 'clear', 'gen_vscode.selections', '编辑区选区 / 输入框选区看得出, 选中的字可读; 从原选区色出发只动必要的一侧'),
    # ---- 刺眼 ----
    'white_cap': (True, 'glare', 'themes.adapt / gen_vscode.white_cap', '深色主题里近纯白(#FFF 这类, OKLCH 明度 >= 0.95 且彩度 <= 0.04)的正文, 界面字 / 图标 / 线, 语法色与终端白压到明度 0.88, 色相不变; 用户定: 只有这一类按刺眼处理'),
}
KINDS = dict(clear='看不清', glare='刺眼')


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
