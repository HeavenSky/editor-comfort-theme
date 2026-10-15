# /// script
# requires-python = ">=3.11"
# ///
# 从本机 VS Code 安装包提取颜色注册表(registerColor), 写入 assets/vscode/color-registry.json.
# 每个键记录 dark / light 下的默认值: 硬编码字面量记为 "#RRGGBB[AA]", 由其他颜色推导或无默认色记为 null;
# transparent: 注册时要求半透明(needsTransparency, 不透明会遮住下面的内容); deprecated: 已废弃(带 deprecationMessage).
# 另记 semanticSelector: semanticTokenColors 键必须匹配的正则; 这三项供 schema.py 按 vscode://schemas/color-theme 校验主题.
# 用法: uv run tools/gen/extract_registry.py [VS Code.app 路径]   (VS Code 升级后重跑, 再运行 gen_vscode.py)
import json, os, re, sys

APP = sys.argv[1] if len(sys.argv) > 1 else '/Applications/Visual Studio Code.app'
RES = os.path.join(APP, 'Contents', 'Resources', 'app')
BUNDLE = os.path.join(RES, 'out', 'vs', 'workbench', 'workbench.desktop.main.js')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'vscode', 'color-registry.json')
NAMED = {'white': 'FFFFFF', 'black': '000000', 'blue': '0000FF', 'lightgrey': 'D3D3D3'}


def literal(expr: str, color_cls: str) -> str | None:
    expr = expr.strip()
    if m := re.fullmatch(r'"#([0-9A-Fa-f]{3,8})"', expr):
        s = m.group(1)
        return '#' + (''.join(c * 2 for c in s) if len(s) in (3, 4) else s).upper()
    if m := re.fullmatch(re.escape(color_cls) + r'\.fromHex\("#([0-9A-Fa-f]{6,8})"\)(?:\.transparent\((\.?\d*\.?\d+)\))?', expr):
        hexv, a = m.group(1).upper(), m.group(2)
        return '#' + (hexv[:6] + '%02X' % round(float(a) * 255) if a else hexv)
    if m := re.fullmatch(re.escape(color_cls) + r'\.(\w+)', expr):
        return '#' + NAMED[m.group(1)] if m.group(1) in NAMED else None
    return None


def main() -> int:
    src = open(BUNDLE, encoding='utf-8', errors='replace').read()
    version = json.load(open(os.path.join(RES, 'package.json')))['version']
    # 前面要有标识符边界: 压缩后注册函数名很短(如 ae), 不加边界会把 Qae( / Iae( 这类同尾的其他调用当成颜色注册
    register = re.search(r'(?<![\w$.])([\w$]+)\("editor\.background",\{', src).group(1)
    color_cls = re.search(r'([\w$]+)\.fromHex\("#', src).group(1)
    # 默认值的四种写法: null, {dark, light, ...}, "#RRGGBB" 字面量, 变量或 Color.fromHex(...) 表达式
    pat = re.compile(r'(?<![\w$.])' + re.escape(register) + r'\("([A-Za-z][\w.\-]*)",(null|\{[^{}]*\}|"[^"]*"|[\w$.]+(?:\([^()]*\))?(?:\.[\w$]+\([^()]*\))*)')
    # registerColor(id, defaults, description, needsTransparency = false, deprecationMessage)
    tail = re.compile(r'\s*,\s*(?:[\w$.]+\([^()]*\)|"[^"]*"|[\w$.]+)\s*(?:,\s*(!0|!1|true|false|void 0))?\s*(?:,\s*([\w$.]+\([^()]*\)|"[^"]*"))?\s*\)')
    colors = {}
    for m in pat.finditer(src):
        key, val = m.group(1), m.group(2)
        if key in colors:
            continue
        entry = {}
        for mode in ('dark', 'light'):
            mm = re.search(r'(?<![\w$])' + mode + r':((?:[^,}()]|\([^()]*\))+)', val) if val.startswith('{') else None
            entry[mode] = literal(mm.group(1) if mm else val, color_cls) if val != 'null' else None
        t = tail.match(src, m.end())
        entry['transparent'] = bool(t and t.group(1) in ('!0', 'true'))
        entry['deprecated'] = bool(t and t.group(2))
        colors[key] = entry
    # 终端 16 色先写进 {"terminal.ansiBlack": {index, defaults: {light, dark, ...}}} 映射表, 再循环注册
    for m in re.finditer(r'"(terminal\.ansi\w+)":\{index:\d+,defaults:\{([^{}]*)\}\}', src):
        modes = dict(re.findall(r'(\w+):"(#[0-9A-Fa-f]{3,8})"', m.group(2)))
        colors.setdefault(m.group(1), {mode: literal(f'"{modes[mode]}"', color_cls) if mode in modes else None for mode in ('dark', 'light')}
                          | {'transparent': False, 'deprecated': False})
    # 内置扩展在 package.json 的 contributes.colors 里声明的颜色(如 git 的 gitDecoration.*)同样进入 schema
    for ext in sorted(os.listdir(os.path.join(RES, 'extensions'))):
        pj = os.path.join(RES, 'extensions', ext, 'package.json')
        if not os.path.isfile(pj):
            continue
        for c in json.load(open(pj, encoding='utf-8')).get('contributes', {}).get('colors', []):
            d = c.get('defaults') or {}
            colors.setdefault(c['id'], {mode: literal(f'"{d[mode]}"', color_cls) if isinstance(d.get(mode), str) else None for mode in ('dark', 'light')}
                              | {'transparent': False, 'deprecated': False})
    if len(colors) < 500:
        print(f'只解析到 {len(colors)} 个颜色键, VS Code 打包形态可能变了, 未写入', file=sys.stderr)
        return 1
    # 语义 token 选择器: Hrr = ^(id|\*)(\.id)*(:id)?$, id = \w+[-_\w+]*; 打包后变量名会变, 只按形态核对
    ident = r'\w+[-_\w+]*'
    if f'"{ident}"'.replace('\\', '\\\\') not in src:
        print('未找到语义 token id 的正则定义, VS Code 打包形态可能变了, 未写入', file=sys.stderr)
        return 1
    selector = rf'^({ident}|\*)(\.{ident})*(:{ident})?$'
    json.dump({'vscodeVersion': version, 'semanticSelector': selector, 'colors': dict(sorted(colors.items()))},
              open(OUT, 'w', encoding='utf-8'), indent='\t')
    hard = sum(1 for v in colors.values() if v['dark'])
    trans = sum(1 for v in colors.values() if v['transparent'])
    dep = sum(1 for v in colors.values() if v['deprecated'])
    print(f'VS Code {version}: {len(colors)} 个颜色键, dark 下硬编码默认值 {hard} 个, 须半透明 {trans} 个, 已废弃 {dep} 个 -> {os.path.relpath(OUT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
