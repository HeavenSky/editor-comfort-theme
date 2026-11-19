# /// script
# requires-python = ">=3.11"
# ///
"""使用仓库的 VS Code 注册表快照校验主题, 只读.

Usage:
  uv run tools/check/schema.py [--complete] <主题.json>...
  uv run tools/check/schema.py -h

Options:
  默认检查未注册键、废弃键和不符合 schema 的值.
  --complete  额外要求 colors 显式提供十六进制颜色. 范围为注册表中对应明暗模式
              下有硬编码默认色的未废弃键. 由其他颜色推导默认值的键交给 VS Code 回退.
              按主题 type 或 -dark.json / -light.json 后缀识别明暗.

Examples:
  # 检测原始主题的缺失项. null 也会被报告为缺少显式颜色.
  uv run tools/check/schema.py --complete assets/source/*.json
  # 重新生成中间主题与发布主题. 补全阶段把原主题的 null 当作未定义.
  npm run gen:themes
  # 复查补全结果. npm run check 和 CI 也会在生成链中检查缺失键.
  uv run tools/check/schema.py --complete assets/full-theme/*-full.json themes/*.json

更新 VS Code 后, 先运行 npm run extract:vscode 刷新 assets/vscode/color-registry.json,
再运行 npm run gen:themes 并复查产物.

有问题时逐条列出并退出码 1.
"""
import argparse, json, os, re, sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
from themefile import load

REGISTRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'vscode', 'color-registry.json')

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


def hardcoded_defaults(reg: dict, mode: str) -> dict[str, str]:
    """对应明暗模式下, 补全要覆盖的未废弃硬编码默认色."""
    return {k: v[mode] for k, v in reg['colors'].items() if v.get(mode) and not v.get('deprecated')}


def coverage_problems(theme: dict, reg: dict, mode: str) -> list[str]:
    colors = theme.get('colors') or {}
    missing = []
    for key in hardcoded_defaults(reg, mode):
        value = colors.get(key)
        if not isinstance(value, str) or not HEX.fullmatch(value):
            missing.append(f'colors.{key}: 缺少显式颜色')
    return missing


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


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help', action='store_true')
    parser.add_argument('--complete', action='store_true')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()
    if args.help or not args.files:
        print(__doc__)
        return 0 if args.help else 2
    reg, bad = registry(), 0
    for f in args.files:
        theme = load(f)
        ps = problems(theme, reg)
        if args.complete:
            mode = theme.get('type') or os.path.basename(f).removesuffix('.json').rsplit('-', 1)[-1]
            if mode in ('dark', 'light'):
                ps.extend(coverage_problems(theme, reg, mode))
            else:
                ps.append('无法识别主题明暗, 请提供 type 或 -dark.json / -light.json 文件名')
        if ps:
            bad += 1
            print(f'{f}: {len(ps)} 个问题')
            for p in ps:
                print(f'  - {p}')
    if not bad:
        checks = '并通过补全键校验' if args.complete else ''
        print(f'{len(args.files)} 个主题全部符合 vscode://schemas/color-theme{checks}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
