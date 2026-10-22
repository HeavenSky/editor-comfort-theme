# /// script
# requires-python = ">=3.11"
# ///
# 从本机 VS Code 安装包提取颜色注册表(registerColor), 写入 assets/vscode/color-registry.json.
# 每个键记录 dark / light 下的默认值: 硬编码字面量记为 "#RRGGBB[AA]", 由其他颜色推导或无默认色记为 null;
#   默认值表达式用 extract_key_docs.py 的解析器求值(与 color-docs.json 的 defaults 一致), 结果是字面色才记;
#   透明度系数键(*.opacity / *Opacity, 只用 alpha 通道, 不是颜色)一律记 null, 不当硬编码默认色补进主题.
# transparent: 注册时要求半透明(needsTransparency, 不透明会遮住下面的内容); deprecated: 已废弃(带 deprecationMessage).
# 另记 semanticSelector: semanticTokenColors 键必须匹配的正则; 这三项供 schema.py 按 vscode://schemas/color-theme 校验主题.
# 本文件只提供 build(); 入口是 tools/gen/extract_vscode.py(npm run extract:vscode).
import json, os, re

import extract_key_docs as kd

LITERAL = re.compile(r'#[0-9A-F]{6}(?:[0-9A-F]{2})?')
OPACITY = re.compile(r'(?:\.o|O)pacity$')


def literal(v) -> str | None:
    """渲染结果或 "#hex" 字符串 -> 归一后的 "#RRGGBB[AA]"; 推导表达式, 键名引用与 null 返回 None."""
    if isinstance(v, str) and re.fullmatch(r'#[0-9A-Fa-f]{3,8}', v):
        v = '#' + (''.join(c * 2 for c in v[1:]) if len(v) in (4, 5) else v[1:]).upper()
    return v if isinstance(v, str) and LITERAL.fullmatch(v) else None


def hardcoded(src: str) -> dict:
    """workbench 内注册的键 -> {dark, light} 硬编码默认值; 解析失败的项记 None(与 color-docs.json 里的 '?' 对应)."""
    ctx, calls = kd.scan(src, [])
    out = {}
    for key, args, _, _ in calls:
        if key is None or key in out:
            continue
        out[key] = {}
        for mode in ('dark', 'light'):
            try:
                v = kd.render_default(ctx, args[1], mode) if len(args) > 1 else None
            except kd.RENDER_ERRORS:
                v = None
            out[key][mode] = None if OPACITY.search(key) else literal(v)
    return out


def build(res: str, src: str, version: str) -> dict | str:
    """res / src 同 extract_key_docs.build. 返回 color-registry.json 的内容; 安装包形态不认识时返回原因, 不写文件."""
    # 前面要有标识符边界: 压缩后注册函数名很短(如 ae), 不加边界会把 Qae( / Iae( 这类同尾的其他调用当成颜色注册
    register = re.search(r'(?<![\w$.])([\w$]+)\("editor\.background",\{', src).group(1)
    hard = hardcoded(src)
    # 默认值的四种写法: null, {dark, light, ...}, "#RRGGBB" 字面量, 变量或 Color.fromHex(...) 表达式; 这里只用来定位键与尾部参数
    pat = re.compile(r'(?<![\w$.])' + re.escape(register) + r'\("([A-Za-z][\w.\-]*)",(null|\{[^{}]*\}|"[^"]*"|[\w$.]+(?:\([^()]*\))?(?:\.[\w$]+\([^()]*\))*)')
    # registerColor(id, defaults, description, needsTransparency = false, deprecationMessage)
    tail = re.compile(r'\s*,\s*(?:[\w$.]+\([^()]*\)|"[^"]*"|[\w$.]+)\s*(?:,\s*(!0|!1|true|false|void 0))?\s*(?:,\s*([\w$.]+\([^()]*\)|"[^"]*"))?\s*\)')
    colors = {}
    for m in pat.finditer(src):
        key = m.group(1)
        if key in colors:
            continue
        entry = {mode: hard.get(key, {}).get(mode) for mode in ('dark', 'light')}
        t = tail.match(src, m.end())
        entry['transparent'] = bool(t and t.group(1) in ('!0', 'true'))
        entry['deprecated'] = bool(t and t.group(2))
        colors[key] = entry
    # 终端 16 色先写进 {"terminal.ansiBlack": {index, defaults: {light, dark, ...}}} 映射表, 再循环注册
    for m in re.finditer(r'"(terminal\.ansi\w+)":\{index:\d+,defaults:\{([^{}]*)\}\}', src):
        modes = dict(re.findall(r'(\w+):"(#[0-9A-Fa-f]{3,8})"', m.group(2)))
        colors.setdefault(m.group(1), {mode: literal(modes.get(mode)) for mode in ('dark', 'light')}
                          | {'transparent': False, 'deprecated': False})
    # 内置扩展在 package.json 的 contributes.colors 里声明的颜色(如 git 的 gitDecoration.*)同样进入 schema
    for ext in sorted(os.listdir(os.path.join(res, 'extensions'))):
        pj = os.path.join(res, 'extensions', ext, 'package.json')
        if not os.path.isfile(pj):
            continue
        for c in json.load(open(pj, encoding='utf-8')).get('contributes', {}).get('colors', []):
            d = c.get('defaults') or {}
            colors.setdefault(c['id'], {mode: literal(d.get(mode)) for mode in ('dark', 'light')}
                              | {'transparent': False, 'deprecated': False})
    if len(colors) < 500:
        return f'只解析到 {len(colors)} 个颜色键, VS Code 打包形态可能变了'
    # 语义 token 选择器: Hrr = ^(id|\*)(\.id)*(:id)?$, id = \w+[-_\w+]*; 打包后变量名会变, 只按形态核对
    ident = r'\w+[-_\w+]*'
    if f'"{ident}"'.replace('\\', '\\\\') not in src:
        return '未找到语义 token id 的正则定义, VS Code 打包形态可能变了'
    selector = rf'^({ident}|\*)(\.{ident})*(:{ident})?$'
    return {'vscodeVersion': version, 'semanticSelector': selector, 'colors': dict(sorted(colors.items()))}

