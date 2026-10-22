# /// script
# requires-python = ">=3.11"
# ///
# 补全段: 原主题 assets/source/<name>.json -> 中间主题 assets/full-theme/<name>-full.json(同 jq . 的格式), 是调色链的输入, 也是全关时的产物.
# 只做格式规范与完整性补全, 不改原主题已有的颜色与规则:
#   1. 格式: 颜色统一成大写 #RRGGBB(AA); 非 hex 的语法前景(如 inherit)VS Code 不认, 丢掉; schema 清理(gen_vscode.conform)
#   2. 界面颜色键: 编辑区 / 终端的底色, 前景, 光标, 输入框选区缺了就补; 终端 6 彩色与亮色缺了按色槽取原主题的语法色补(fill_terminal);
#      VS Code 硬编码默认色的键按终端色同色相补
#   3. 语法规则: 按 assets/pool/full-rule.json 严格增量补 —— 原主题规则原样保留, 池里的选择器只在原主题解析不出颜色时补, 补的规则放最前;
#      full-rule.json 的 skip 记各主题经分词实测会改掉原主题已上色 token 的池选择器(外层上色, 内层被补), 不补
#   4. 语义色原样保留
# 中间主题都不进版本库(assets/full-theme/ 整个忽略); 补全段的漂移由 gen_vscode.py --check 核对 themes/ 生成物暴露.
# 用法: uv run tools/gen/complete.py   写出全部中间主题
#       uv run tools/gen/complete.py --guard   用 tools/textmate/pool-guard.mjs 对 tools/samples 分词实测, 重算 full-rule.json 的 skip(npm run pool:update 的第二步)
import itertools, json, os, subprocess, sys

# 补全复用 gen_vscode 的映射与补色函数, 但一律在全关下运行: 不让任何调色步骤混进补全段
os.environ['COMFORT_STEPS'] = 'none'
sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', d) for d in ('lib', 'gen', 'check', 'lab')]
import math

from colorlib import blend, cr, de2000, from_oklch, h, hue_deg, hue_in, hx, lum, oklch, sat, with_sat
from comfort import STATUS_GROUPS, TERM_COLORS, TERM_HUES
from gen_vscode import ANSI, FULL, NEUTRAL_CHROMA, REGISTRY, SOURCES, TEXT_ON_CODE, Mapper, conform, load, opaque, parse, scopes_of, source_fg
import pool

FULL_RULE = pool.FULL_RULE
# 原主题不定义括号色时, 用原主题的 数字 / 关键字 / 转义 色补上, 而不是落到注册表的通用补色
BRACKET_FALLBACK = ['constant.numeric', 'keyword.control', 'constant.character.escape']
SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'samples')


def full_path(name: str) -> str:
    return os.path.join(FULL, f'{name}-full.json')


def norm(v):
    """颜色统一成大写 #RRGGBB(AA)(含 white / black 这类颜色名); 不是颜色的原样返回."""
    p = parse(v)
    return hx(p[0]) + p[1] if p else v


def pool_rules(name: str, rules: list, fg: str, guard: bool = True) -> list[dict]:
    """full-rule.json 里原主题解析不出颜色的选择器, 按角色成组补规则; 颜色取原主题该角色的颜色(pool.role_value).
    guard: 跳过 skip 里记的本主题选择器(--guard 重算 skip 时关掉)."""
    data = json.load(open(FULL_RULE, encoding='utf-8'))
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
        settings = {'foreground': norm(pool.role_value(rules, role, fg))}
        if pool.ROLES.get(role, (None, None))[1]:
            settings['fontStyle'] = pool.ROLES[role][1]
        out.append({'name': f'Pool {role}', 'scope': sels, 'settings': settings})
    return out


def resolve(rules: list, scope: str) -> str | None:
    # 选择器是 scope 的点分前缀即命中, 最长者胜; 只用于补括号色, 不处理后代选择器
    best, color = -1, None
    for r in rules:
        fg = r.get('settings', {}).get('foreground')
        for sel in scopes_of(r):
            if fg and ' ' not in sel and (scope == sel or scope.startswith(sel + '.')) and len(sel) > best:
                best, color = len(sel), fg
    return color


def hardcoded_keys(dark: bool) -> dict[str, str]:
    """VS Code 注册表中默认值是硬编码字面量的键 -> 该默认值; 主题不定义这些键时界面会落到与主题无关的颜色."""
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    mode = 'dark' if dark else 'light'
    return {k: v[mode] for k, v in reg['colors'].items() if v.get(mode) and not v.get('deprecated')}


def is_area(key: str) -> bool:
    """画成一片的颜色(底色, 边框, 阴影): 补色不按 VS Code 默认色的对比度提明度; 其余(文字, 图标)按 default_cr 提."""
    return key.lower().endswith(('background', 'border', 'shadow'))


def _near(hues: list, H: float) -> tuple:
    return min(hues, key=lambda x: abs(math.atan2(math.sin(x[0] - H), math.cos(x[0] - H))))


def accent(hues: list, v) -> str | None:
    """VS Code 默认的彩色映射到本主题同色相的终端色, 保留原透明度; 中性色返回 None."""
    p = parse(v)
    if p is None or oklch(p[0])[1] < NEUTRAL_CHROMA:
        return None
    return hx(_near(hues, oklch(p[0])[2])[1]) + p[1]


def tint(hues: list, v, bg, ref_bg) -> str | None:
    """背景类默认色: 色相取本主题同色相的终端色, 明度保留默认值(随底色平移), 彩度不变; 不把暗底色换成亮色块."""
    p = parse(v)
    if p is None:
        return None
    L, C, H = oklch(p[0])
    if C < NEUTRAL_CHROMA:
        return None
    L += oklch(bg)[0] - oklch(ref_bg)[0]
    return hx(from_oklch(L, C, oklch(_near(hues, H)[1])[2])) + p[1]


def fill_hardcoded(colors: dict, t: dict, m: Mapper, hues: list) -> None:
    # 注册表里默认值硬编码的键, 主题没定义的一律按本主题色板补齐, 不让任何界面落到与主题无关的颜色
    hard = hardcoded_keys(t['dark'])
    vs_bg = parse(hard['editor.background'])[0]
    for k, default in hard.items():
        if k in colors:
            continue
        # 默认值全透明的(如括号色 4~6 的 #00000000, 表示不着色)原样保留; 混到底色上会变成与底同色的不透明色, 字就看不见了
        p = parse(default)
        if p and p[1] == '00':
            colors[k] = default
            continue
        if k.startswith(TEXT_ON_CODE):
            out = m.token(default)
        elif k.lower().endswith('background'):
            out = tint(hues, default, t['bg'], vs_bg)
        else:
            out = accent(hues, default)
            out = out and (out if is_area(k) else default_cr(out, default, t['bg'], vs_bg))
        colors[k] = out or m.ui(default, vs_bg)


# 补出的界面文字色对底色的对比度要求上限: 与看不清类步骤的正文 / 语法 / 终端可读下限一致
FILL_TEXT_CR = 4.5


def default_cr(v: str, default: str, bg, vs_bg) -> str:
    """补出的界面文字 / 图标色(色相取终端色)对本主题底色的对比度不低于 VS Code 默认色对默认底色的对比度, 但最多要求到 FILL_TEXT_CR:
    明度往远离底色的方向调, 色相与饱和度不变, 保留透明度. 浅色主题的终端黄(如 Owl Light #E0AF02)直接拿来当 git 修改标记会比默认棕色浅;
    VS Code 深色默认色对比度多在 9~10, 不封顶会把深色主题本来够读的终端色都提成浅色, 偏离原主题."""
    (rgb, alpha), (drgb, dalpha) = parse(v), parse(default)
    a = int(alpha, 16) / 255 if alpha else 1.0
    goal = min(FILL_TEXT_CR, cr(blend(drgb, vs_bg, int(dalpha, 16) / 255) if dalpha else drgb, vs_bg))
    L, _, H = oklch(rgb)
    s, step, out = sat(rgb), (0.004 if lum(rgb) >= lum(bg) else -0.004), rgb
    while cr(blend(out, bg, a), bg) < goal and 0 < L + step < 1:
        L += step
        out = with_sat(L, s, H)
    return hx(out) + alpha


# 状态色组内两两色差目标(门禁清晰理想 15): 原主题没定义而由 fill_hardcoded 补出的状态色, 撞上同组颜色时改取另一个终端色
STATUS_DE = 15.0


def status_apart(colors: dict, src_colors: dict, t: dict, hues: list) -> None:
    bg = t['bg']
    hard = hardcoded_keys(t['dark'])
    vs_bg = parse(hard['editor.background'])[0]
    for group in STATUS_GROUPS:
        for k in group:
            if k in src_colors or k not in colors:
                continue
            others = [opaque(colors, o, bg) for o in group if o != k and o in colors]
            cur = opaque(colors, k, bg)
            if not others or min(de2000(cur, o) for o in others) >= STATUS_DE:
                continue
            cands = [default_cr(v, hard[k], bg, vs_bg) if k in hard and not is_area(k) else v for _, c in hues if (v := accent(hues, hx(c)))]
            colors[k] = max(cands, key=lambda v: min(de2000(parse(v)[0], o) for o in others))


def fill_terminal(colors: dict, rules: list, dark: bool) -> None:
    """原主题没定义的终端 6 彩色按色槽(comfort.TERM_HUES)取原主题的彩色语法色: 每槽取色相落在槽内, 离槽中心最近且不与别的槽重复的;
    槽里没有就用 VS Code 默认色. 没定义的亮色: 深色主题按 VS Code 默认 普通色 -> 亮色 的明度差平移, 色相与彩度不变; 浅色主题与普通色相同
    (默认亮色更浅, 在浅底上反而更淡, 再被终端下限压回来时彩度会走样, 如 One Light 亮红成了 #E9010E). 黑白灰由 fill_hardcoded 补.
    不按色相就近套 VS Code 默认色: 浅色默认的黄是偏绿的橄榄色, 就近会取到绿色(原 One Light 绿黄同色)."""
    reg = hardcoded_keys(dark)
    key = lambda n: f'terminal.ansi{n}'
    missing = [n for n in TERM_COLORS if key(n) not in colors]
    if missing:
        have = {hx(parse(colors[key(n)])[0]) for n in TERM_COLORS if key(n) in colors}
        # diff / 错误标记色(新增, 删除, 错误)不当终端色: 它们为整行底色设计, 常是很深或很浅的色(如 Night Owl 新增 #036A07)
        syn = {hx(parse(c)[0]) for r in pool.ROLES if r not in ('inserted', 'deleted', 'invalid') and (c := pool.role_value(rules, r, None)) and parse(c)}
        syn = sorted(c for c in syn if oklch(h(c))[1] > NEUTRAL_CHROMA and c not in have)

        def gap(c: str, n: str) -> float:
            lo, hi = TERM_HUES[n]
            mid = (lo + ((hi - lo) % 360) / 2) % 360
            return abs((hue_deg(h(c)) - mid + 180) % 360 - 180)

        opts = [[c for c in syn if hue_in(hue_deg(h(c)), TERM_HUES[n])] + [None] for n in missing]
        best = min((p for p in itertools.product(*opts) if len({c for c in p if c}) == len([c for c in p if c])),
                   key=lambda p: sum(gap(c, n) if c else 180 for c, n in zip(p, missing)))
        for n, c in zip(missing, best):
            colors[key(n)] = c or norm(reg[key(n)])
    for n in TERM_COLORS:
        if key('Bright' + n) in colors:
            continue
        if not dark:
            colors[key('Bright' + n)] = colors[key(n)]
            continue
        L, C, H = oklch(parse(colors[key(n)])[0])
        dl = oklch(parse(reg[key('Bright' + n)])[0])[0] - oklch(parse(reg[key(n)])[0])[0]
        colors[key('Bright' + n)] = hx(from_oklch(min(1.0, max(0.0, L + dl)), C, H))


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
    # 终端底色 / 前景 / 光标与输入框选区原主题没定义时, 取 VS Code 实际回落的颜色: 终端底色先取面板底(面板里的终端画在它上面),
    # 没有再取编辑区底; 其余取编辑区的同类颜色. Terminal.app 配置的底色仍是编辑区底(themes.py 的 bg)
    for k, bases in (('terminal.background', ('panel.background', 'editor.background')), ('terminal.foreground', ('editor.foreground',)),
                     ('terminalCursor.foreground', ('editorCursor.foreground',)), ('selection.background', ('editor.selectionBackground',))):
        if k not in colors and (base := next((x for x in bases if x in colors), None)):
            colors[k] = colors[base]
    # 终端彩色先补齐: 它们也是下面补界面色的色源(VS Code 硬编码默认色的键按同色相的终端色补)
    fill_terminal(colors, rules, dark)
    bg = parse(colors['editor.background'])[0]
    t = dict(name=name, dark=dark, bg=bg, fg=h(fg), token_min=0.0, comment_cr=False)
    m = Mapper(t, {'colors': colors, 'tokenColors': rules})
    # 补界面色的色源: 终端 6 彩色(fill_terminal 已补齐)
    hues = [(oklch(c)[2], c) for c in (parse(colors[f'terminal.ansi{n}'])[0] for n in ANSI[1:7])]
    if 'editorBracketHighlight.foreground1' not in colors:
        for i, scope in enumerate(BRACKET_FALLBACK, 1):
            colors[f'editorBracketHighlight.foreground{i}'] = norm(resolve(rules, scope) or fg)
    original = dict(colors)
    fill_hardcoded(colors, t, m, hues)
    status_apart(colors, original, t, hues)
    conform(colors, rules, semantic, t)
    colors = {k: norm(v) for k, v in colors.items()}
    rules[:0] = pool_rules(name, rules, fg, guard)
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
        added = [r for r in rules if r.get('name', '').startswith('Pool ')]
        themes[name] = {'rules': rules[len(added):], 'pool': [s for r in added for s in r['scope']]}
    files = [os.path.join(SAMPLES, f) for f in sorted(os.listdir(SAMPLES)) if not f.startswith('.')]
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
