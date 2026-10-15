# /// script
# requires-python = ">=3.11"
# ///
# 补全段: 原主题 assets/source/<name>.json -> 中间主题 assets/full-theme/<name>-full.json(同 jq . 的格式), 是调色链的输入, 也是全关时的产物.
# 只做格式规范与完整性补全, 不改原主题已有的颜色与规则:
#   1. 格式: 颜色统一成大写 #RRGGBB(AA); 非 hex 的语法前景(如 inherit)VS Code 不认, 丢掉; schema 清理(gen_vscode.conform)
#   2. 界面颜色键: 编辑区 / 终端的底色, 前景, 光标, 输入框选区缺了就补; VS Code 硬编码默认色的键按原主题终端色(没有终端色的按语法色)同色相补
#   3. 语法规则: 按 assets/source/full-rule.json 严格增量补 —— 原主题规则原样保留, 池里的选择器只在原主题解析不出颜色时补, 补的规则放最前;
#      full-rule.json 的 skip 记各主题经分词实测会改掉原主题已上色 token 的池选择器(外层上色, 内层被补), 不补
#   4. 语义色原样保留
# 中间主题都不进版本库(assets/full-theme/ 整个忽略); 补全段的漂移由 gen_vscode.py --check 核对 themes/ 生成物暴露.
# 用法: uv run tools/gen/complete.py   写出全部中间主题
#       uv run tools/gen/complete.py --guard   用 tools/textmate/pool-guard.mjs 对 tools/samples 分词实测, 重算 full-rule.json 的 skip(npm run pool:update 的最后一步)
import json, os, subprocess, sys

# 补全复用 gen_vscode 的映射与补色函数, 但一律在全关下运行: 不让任何调色步骤混进补全段
os.environ['COMFORT_STEPS'] = 'none'
sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', d) for d in ('lib', 'gen', 'check', 'lab')]
from colorlib import h, hx, oklch
from gen_vscode import (ANSI, BRACKET_FALLBACK, FULL, NEUTRAL_CHROMA, REGISTRY, SOURCES, Mapper, conform, fill_hardcoded, load, parse, resolve,
                        source_fg, status_apart)
import pool

FULL_RULE = os.path.join(SOURCES, 'full-rule.json')
SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'samples')


def full_path(name: str) -> str:
    return os.path.join(FULL, f'{name}-full.json')


def norm(v):
    """颜色统一成大写 #RRGGBB(AA)(含 white / black 这类颜色名); 不是颜色的原样返回."""
    p = parse(v)
    return hx(p[0]) + p[1] if p else v


def pool_rules(name: str, rules: list, colors: dict, fg: str, guard: bool = True) -> list[dict]:
    """full-rule.json 里原主题解析不出颜色的选择器, 按角色成组补规则; 颜色取 角色 -> 主题颜色键(本主题记录优先, 否则默认键).
    guard: 跳过 skip 里记的本主题选择器(--guard 重算 skip 时关掉)."""
    data = json.load(open(FULL_RULE, encoding='utf-8'))
    cmap = {**data['colors'].get('default', {}), **data['colors'].get(name, {})}
    skip = set(data.get('skip', {}).get(name, [])) if guard else set()
    groups: dict[str, list[str]] = {}
    for sel, role in data['rules'].items():
        if sel in skip:
            continue
        # 后代选择器按最右一段判断: 原主题已给这段上色时不补, 免得更具体的池规则盖掉原主题的颜色
        if pool.lookup(rules, sel.split()[-1]) is None:
            groups.setdefault(role, []).append(sel)
    out = []
    for role, sels in groups.items():
        key = cmap.get(role)
        color = key if key and key.startswith('#') else colors.get(key) if key else None
        color = norm(color) if parse(color) else norm(pool.role_value(rules, role, fg))
        settings = {'foreground': color}
        if pool.ROLES.get(role, (None, None))[1]:
            settings['fontStyle'] = pool.ROLES[role][1]
        out.append({'name': f'Pool {role}', 'scope': sels, 'settings': settings})
    return out


def complete(name: str, dark: bool, guard: bool = True) -> dict:
    src = load(os.path.join(SOURCES, f'{name}.json'))
    reg = json.load(open(REGISTRY, encoding='utf-8'))['colors']
    mode = 'dark' if dark else 'light'
    colors = {k: norm(v) for k, v in src.get('colors', {}).items()}
    rules = json.loads(json.dumps(src.get('tokenColors', [])))
    for r in rules:
        st = r.get('settings')
        if isinstance(st, dict) and 'foreground' in st:
            if parse(st['foreground']) is None:
                del st['foreground']
            else:
                st['foreground'] = norm(st['foreground'])
    semantic = {k: (norm(v) if isinstance(v, str) else {**v, **({'foreground': norm(v['foreground'])} if 'foreground' in v else {})})
                for k, v in (src.get('semanticTokenColors') or {}).items()}
    fg = norm(source_fg(src, dark))
    colors.setdefault('editor.background', norm(reg['editor.background'][mode]))
    colors.setdefault('editor.foreground', fg)
    # 终端底色 / 前景 / 光标与输入框选区原主题没定义时, 取编辑区的同类颜色(Terminal.app 主题与 VS Code 终端同用)
    for k, base in (('terminal.background', 'editor.background'), ('terminal.foreground', 'editor.foreground'),
                    ('terminalCursor.foreground', 'editorCursor.foreground'), ('selection.background', 'editor.selectionBackground')):
        if k not in colors and base in colors:
            colors[k] = colors[base]
    bg = parse(colors['editor.background'])[0]
    t = dict(name=name, dark=dark, bg=bg, fg=h(fg), cap=1.0, token_min=0.0, comment_cr=None, syntax_max=None,
             ansi={n: parse(colors[f'terminal.ansi{n}'])[0] for n in ANSI if f'terminal.ansi{n}' in colors})
    t['ui_ansi'] = {n: t['ansi'].get(n, t['fg']) for n in ANSI}
    m = Mapper(t, {'colors': colors, 'tokenColors': rules})
    # 补色的色源: 原主题的终端彩色; 没有终端色时取原主题的彩色语法色
    if not all(f'terminal.ansi{n}' in colors for n in ANSI[1:7]):
        syn = {parse(c)[0] for r in pool.ROLES if (c := pool.role_value(rules, r, None)) and parse(c)}
        m.hues = [(oklch(c)[2], c) for c in syn if oklch(c)[1] > NEUTRAL_CHROMA] or m.hues
    if 'editorBracketHighlight.foreground1' not in colors:
        for i, scope in enumerate(BRACKET_FALLBACK, 1):
            colors[f'editorBracketHighlight.foreground{i}'] = norm(resolve(rules, scope) or fg)
    original = dict(colors)
    fill_hardcoded(colors, t, m)
    status_apart(colors, original, t, m)
    conform(colors, rules, semantic, t)
    colors = {k: norm(v) for k, v in colors.items()}
    rules[:0] = pool_rules(name, rules, colors, fg, guard)
    return {
        '$schema': 'vscode://schemas/color-theme',
        'name': src.get('name', name),
        'type': 'dark' if dark else 'light',
        'semanticHighlighting': src.get('semanticHighlighting', True),
        'colors': dict(sorted(colors.items())),
        'tokenColors': rules,
        'semanticTokenColors': semantic,
    }


def names() -> list[tuple[str, bool]]:
    out = []
    for f in sorted(os.listdir(SOURCES)):
        n = f[:-5]
        if f.endswith('.json') and n.endswith(('-dark', '-light')):
            out.append((n, n.endswith('-dark')))
    return out


def guard() -> None:
    """不带 skip 补全各主题, 把原主题规则与池选择器交给 pool-guard.mjs 分词实测, 结果整体重写 full-rule.json 的 skip."""
    themes = {}
    for name, dark in names():
        rules = complete(name, dark, guard=False)['tokenColors']
        pool = [r for r in rules if r.get('name', '').startswith('Pool ')]
        themes[name] = {'rules': rules[len(pool):], 'pool': [s for r in pool for s in r['scope']]}
    files = [os.path.join(SAMPLES, f) for f in sorted(os.listdir(SAMPLES))]
    out = subprocess.run(['node', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'textmate', 'pool-guard.mjs')],
                         input=json.dumps({'files': files, 'themes': themes}), capture_output=True, text=True, check=True).stdout
    skip = {n: v for n, v in sorted(json.loads(out).items()) if v}
    data = json.load(open(FULL_RULE, encoding='utf-8'))
    data['skip'] = skip
    open(FULL_RULE, 'w', encoding='utf-8').write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print(f'full-rule.json skip: {sum(map(len, skip.values()))} 个选择器, ' + ', '.join(f'{n} {len(v)}' for n, v in skip.items()))


def main() -> int:
    if '--guard' in sys.argv:
        guard()
        return 0
    os.makedirs(FULL, exist_ok=True)
    for name, dark in names():
        text = json.dumps(complete(name, dark), indent=2, ensure_ascii=False) + '\n'
        path = full_path(name)
        old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if old == text:
            continue
        open(path, 'w', encoding='utf-8').write(text)
        print('wrote', os.path.relpath(path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
