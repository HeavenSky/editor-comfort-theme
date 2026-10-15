# /// script
# requires-python = ">=3.11"
# ///
# 按 vscode://schemas/color-theme 校验 VS Code 颜色主题; 规则取自 VS Code 源码(颜色注册表 / textmate-colors / token-styling),
# 颜色键的注册, 半透明要求与废弃标记来自 assets/vscode/vscode-color-registry.json(extract_registry.py 提取).
# 用法: uv run tools/check/schema.py <主题.json>...   (有问题时逐条列出并退出码 1)
import json, os, re, sys

sys.dont_write_bytecode = True
REGISTRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'vscode', 'vscode-color-registry.json')

# format: color-hex 接受的写法; 另有 "default" 表示用默认色
HEX = re.compile(r'^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$')
# needsTransparency 的颜色: 必须带透明度且不是完全不透明(4 位末位不为 F, 8 位末两位不为 FF)
TRANSPARENT = re.compile(r'^#(?:[0-9a-fA-F]{3}[0-9a-eA-E]|[0-9a-fA-F]{6}(?![fF]{2})[0-9a-fA-F]{2})$')
FONT_STYLE = re.compile(r'^(\s*\b(italic|bold|underline|strikethrough))*\s*$')
RULE_KEYS = {'name', 'scope', 'settings'}
SETTINGS_KEYS = {'foreground', 'background', 'fontStyle', 'fontFamily', 'fontSize', 'lineHeight'}
SEMANTIC_STYLE_KEYS = {'foreground', 'background', 'fontStyle', 'bold', 'italic', 'underline', 'strikethrough'}


def registry() -> dict:
    return json.load(open(REGISTRY_PATH, encoding='utf-8'))


def problems(theme: dict, reg: dict | None = None) -> list[str]:
    """返回主题违反 schema 的问题; 空列表表示通过. 已废弃项(deprecationMessage)与不再生效的字段也计为问题."""
    reg = reg or registry()
    colors, out = reg['colors'], []
    for k, v in (theme.get('colors') or {}).items():
        info = colors.get(k)
        if info is None:
            out.append(f'colors.{k}: 未注册的颜色键, VS Code 会忽略')
            continue
        if info.get('deprecated'):
            out.append(f'colors.{k}: 已废弃的颜色键')
        if not isinstance(v, str) or not (HEX.match(v) or v == 'default'):
            out.append(f'colors.{k}: 颜色值 {v!r} 不是 #RGB / #RGBA / #RRGGBB / #RRGGBBAA')
        elif info.get('transparent') and v != 'default' and not TRANSPARENT.match(v):
            out.append(f'colors.{k}: {v} 必须半透明, 不透明会遮住下面的内容')
    rules = theme.get('tokenColors')
    if isinstance(rules, list):
        for i, r in enumerate(rules):
            where = f"tokenColors[{i}]{' ' + r['name'] if isinstance(r, dict) and r.get('name') else ''}"
            if not isinstance(r, dict) or not isinstance(r.get('settings'), dict):
                out.append(f'{where}: 缺少 settings')
                continue
            for extra in sorted(set(r) - RULE_KEYS):
                out.append(f'{where}: 不支持的字段 {extra}')
            sc = r.get('scope')
            if sc is not None and not (isinstance(sc, str) or (isinstance(sc, list) and all(isinstance(x, str) for x in sc))):
                out.append(f'{where}: scope 必须是字符串或字符串数组')
            st = r['settings']
            for extra in sorted(set(st) - SETTINGS_KEYS):
                out.append(f'{where}: settings 不支持的字段 {extra}')
            if 'background' in st:
                out.append(f'{where}: settings.background 已废弃, token 背景色不生效')
            if 'foreground' in st and not (isinstance(st['foreground'], str) and HEX.match(st['foreground'])):
                out.append(f"{where}: foreground {st['foreground']!r} 不是 hex 颜色")
            if 'fontStyle' in st and not (isinstance(st['fontStyle'], str) and FONT_STYLE.match(st['fontStyle'])):
                out.append(f"{where}: fontStyle {st['fontStyle']!r} 不合法")
    selector = re.compile(reg['semanticSelector'])
    for k, v in (theme.get('semanticTokenColors') or {}).items():
        where = f'semanticTokenColors.{k}'
        if not selector.match(k):
            out.append(f'{where}: 选择器格式不合法')
        if isinstance(v, str):
            if not HEX.match(v):
                out.append(f'{where}: 颜色值 {v!r} 不是 hex 颜色')
            continue
        if not isinstance(v, dict):
            out.append(f'{where}: 值必须是颜色或样式对象')
            continue
        for extra in sorted(set(v) - SEMANTIC_STYLE_KEYS):
            out.append(f'{where}: 不支持的字段 {extra}')
        if 'background' in v:
            out.append(f'{where}: background 已废弃, 不生效')
        if 'foreground' in v and not (isinstance(v['foreground'], str) and HEX.match(v['foreground'])):
            out.append(f"{where}: foreground {v['foreground']!r} 不是 hex 颜色")
        if 'fontStyle' in v and not (isinstance(v['fontStyle'], str) and FONT_STYLE.match(v['fontStyle'])):
            out.append(f"{where}: fontStyle {v['fontStyle']!r} 不合法")
    if 'semanticHighlighting' in theme and not isinstance(theme['semanticHighlighting'], bool):
        out.append('semanticHighlighting 必须是布尔值')
    return out


def load(path: str) -> dict:
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', s))


def main() -> int:
    files = sys.argv[1:]
    if not files:
        print('用法: uv run tools/check/schema.py <主题.json>...')
        return 2
    reg, bad = registry(), 0
    for f in files:
        ps = problems(load(f), reg)
        if ps:
            bad += 1
            print(f'{f}: {len(ps)} 个问题')
            for p in ps:
                print(f'  - {p}')
    if not bad:
        print(f'{len(files)} 个主题全部符合 vscode://schemas/color-theme')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
