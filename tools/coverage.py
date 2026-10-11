# 语法着色的统一覆盖: 所有主题都必须为下列 scope 给出颜色或字体样式; 原主题没定义的, 从本主题已有的相近角色取色补上.
# gen_vscode.py 用 fill() 补规则, metrics.py 用 missing() 把覆盖率计入门禁.
#
# 不纳入: punctuation 等标点. 引号, 注释符号等标点套在字符串 / 注释里, 匹配时内层 scope 优先,
# 加一条通用的 punctuation 规则会把它们从字符串色 / 注释色改成正文色; 不定义时跟随外层才是对的.
from collections import Counter

FG = 'fg'  # 取不到相近角色时退回正文色

# scope -> (按顺序取色的相近角色, 字体样式); 字体样式不为 None 时只要求定义样式, 颜色有则带上
COVERAGE = {
    'comment': (['comment.line', 'comment.block'], None),
    'string': (['string.quoted', 'string.template'], None),
    'string.regexp': (['constant.character.escape', 'constant.regexp', 'string'], None),
    'constant.numeric': (['constant.language', 'constant'], None),
    'constant.language': (['constant.numeric', 'constant'], None),
    'constant.character.escape': (['constant.character', 'string.regexp', 'constant.numeric'], None),
    'keyword': (['keyword.control', 'storage.type', 'storage'], None),
    'keyword.control': (['keyword', 'storage.type'], None),
    'keyword.operator': (['punctuation.separator', FG], None),
    'storage.type': (['storage', 'keyword'], None),
    'storage.modifier': (['storage', 'keyword'], None),
    'entity.name.function': (['support.function', 'meta.function-call'], None),
    'support.function': (['entity.name.function', 'meta.function-call'], None),
    'entity.name.type': (['entity.name.class', 'support.class', 'support.type', 'storage.type'], None),
    'entity.name.class': (['entity.name.type', 'support.class', 'support.type'], None),
    'entity.name.namespace': (['entity.name.type.namespace', 'entity.name.type.module', 'entity.name.type', 'entity.name.class'], None),
    'entity.other.inherited-class': (['entity.name.class', 'entity.name.type', 'support.class'], None),
    'support.type': (['entity.name.type', 'support.class', 'storage.type'], None),
    'support.class': (['entity.name.class', 'entity.name.type', 'support.type'], None),
    'variable': (['variable.other.readwrite', FG], None),
    'variable.parameter': (['variable.parameter.function', 'variable', FG], None),
    'variable.language': (['variable.language.this', 'keyword', 'storage.type'], None),
    'variable.other.property': (['variable.other.object.property', 'support.type.property-name', 'meta.object-literal.key', 'variable', FG], None),
    'meta.object-literal.key': (['variable.other.property', 'support.type.property-name', 'entity.other.attribute-name', 'variable', FG], None),
    'support.type.property-name': (['meta.object-literal.key', 'variable.other.property', 'entity.other.attribute-name'], None),
    'entity.name.tag': (['entity.name.tag.html', 'keyword', 'storage.type'], None),
    'entity.other.attribute-name': (['entity.other.attribute-name.html', 'variable.other.property', 'constant.numeric'], None),
    'markup.heading': (['markup.heading.markdown', 'entity.name.section', 'entity.name.tag', 'keyword'], 'bold'),
    'markup.bold': (['markup.bold.markdown'], 'bold'),
    'markup.italic': (['markup.italic.markdown'], 'italic'),
    'markup.inline.raw': (['markup.inline.raw.string.markdown', 'markup.raw', 'string'], None),
    'markup.quote': (['markup.quote.markdown', 'comment'], 'italic'),
    'markup.underline.link': (['markup.underline.link.markdown', 'string.other.link', 'constant.numeric'], None),
}


def _scopes(rule: dict) -> list[str]:
    sc = rule.get('scope') or []
    return [x.strip() for x in (sc.split(',') if isinstance(sc, str) else sc) if x.strip()]


def lookup(rules: list, scope: str, field: str = 'foreground') -> str | None:
    """主题对 scope 给出的 field: 选择器是 scope 的点分前缀即命中, 最长者胜(与 VS Code 一致, 不计后代选择器);
    都不命中时退而取只多一段的子 scope(多为语言后缀, 如 markup.heading.markdown)里最常用的值;
    更深的子 scope 往往是另一个角色(如 variable.other.constant 是常量), 不拿来推断."""
    best, value, child = -1, None, Counter()
    for r in rules:
        v = r.get('settings', {}).get(field)
        if v is None:
            continue
        for sel in _scopes(r):
            if ' ' in sel:
                continue
            if (scope == sel or scope.startswith(sel + '.')) and len(sel) > best:
                best, value = len(sel), v
            elif sel.startswith(scope + '.') and '.' not in sel[len(scope) + 1:]:
                child[v] += 1
    return value if value is not None else (child.most_common(1)[0][0] if child else None)


def defined(rules: list, scope: str) -> bool:
    """scope 本身或其前缀被某条规则直接覆盖(不含子 scope 推断)."""
    for r in rules:
        st = r.get('settings', {})
        for sel in _scopes(r):
            if ' ' not in sel and (scope == sel or scope.startswith(sel + '.')):
                if COVERAGE[scope][1] is None and st.get('foreground'):
                    return True
                if COVERAGE[scope][1] is not None and COVERAGE[scope][1] in str(st.get('fontStyle', '')):
                    return True
    return False


def missing(rules: list) -> list[str]:
    return [s for s in COVERAGE if not defined(rules, s)]


def fill(rules: list, fg: str) -> list[dict]:
    """返回需要补到规则表最前面的兜底规则; 放在最前面, 原主题任何同等具体的规则都排在后面而优先生效."""
    out = []
    for scope in missing(rules):
        donors, style = COVERAGE[scope]
        color = None
        for d in donors:
            color = fg if d == FG else lookup(rules, d)
            if color:
                break
        settings = {}
        if color:
            settings['foreground'] = color
        if style:
            settings['fontStyle'] = style
        if settings:
            out.append({'name': f'Comfort coverage: {scope}', 'scope': scope, 'settings': settings})
    return out
