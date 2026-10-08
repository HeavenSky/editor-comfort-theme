# /// script
# requires-python = ">=3.11"
# ///
# 从本机 VS Code 安装包提取颜色注册表(registerColor), 写入 tools/sources/vscode-color-registry.json.
# 每个键记录 dark / light 下的默认值: 硬编码字面量记为 "#RRGGBB[AA]", 由其他颜色推导或无默认色记为 null.
# 用法: uv run tools/extract_registry.py [VS Code.app 路径]   (VS Code 升级后重跑, 再运行 gen_vscode.py)
import json, os, re, sys

APP = sys.argv[1] if len(sys.argv) > 1 else '/Applications/Visual Studio Code.app'
RES = os.path.join(APP, 'Contents', 'Resources', 'app')
BUNDLE = os.path.join(RES, 'out', 'vs', 'workbench', 'workbench.desktop.main.js')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources', 'vscode-color-registry.json')
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
    register = re.search(r'([\w$]+)\("editor\.background",\{', src).group(1)
    color_cls = re.search(r'([\w$]+)\.fromHex\("#', src).group(1)
    pat = re.compile(re.escape(register) + r'\("([A-Za-z][\w.\-]*)",(null|\{[^{}]*\}|[\w$.]+(?:\([^()]*\))?(?:\.[\w$]+\([^()]*\))*)')
    colors = {}
    for m in pat.finditer(src):
        key, val = m.group(1), m.group(2)
        if key in colors:
            continue
        entry = {}
        for mode in ('dark', 'light'):
            mm = re.search(r'(?<![\w$])' + mode + r':((?:[^,}()]|\([^()]*\))+)', val) if val.startswith('{') else None
            entry[mode] = literal(mm.group(1) if mm else val, color_cls) if val != 'null' else None
        colors[key] = entry
    if len(colors) < 500:
        print(f'只解析到 {len(colors)} 个颜色键, VS Code 打包形态可能变了, 未写入', file=sys.stderr)
        return 1
    json.dump({'vscodeVersion': version, 'colors': dict(sorted(colors.items()))}, open(OUT, 'w', encoding='utf-8'), indent='\t')
    hard = sum(1 for v in colors.values() if v['dark'])
    print(f'VS Code {version}: {len(colors)} 个颜色键, dark 下硬编码默认值 {hard} 个 -> {os.path.relpath(OUT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
