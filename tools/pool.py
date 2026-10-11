# /// script
# requires-python = ">=3.11"
# ///
# 语法规则池: 把全部原主题(tools/sources/)的 tokenColors 选择器合并成一个池子, 每个选择器裁决出一个"角色",
# 各主题只提供角色的颜色与字体样式, gen_vscode.py 据此为所有主题生成结构相同的 tokenColors.
#
# 裁决分层(见 decide):
#   0 跟随外层: 标点, meta.* 等包裹 scope 不出规则, 让外层(字符串, 注释等)决定颜色
#   1 结构规则: 按 TextMate 命名约定推出角色, 且没有被多数原主题反对
#   2 无结构规则, 但各原主题的候选角色有交集
#   3/4/5 需人工: 结构规则被多数原主题反对 / 只有一个原主题定义 / 原主题分歧; 未标注前用推荐值
# 人工标注存于 tools/sources/pool-overrides.json({选择器: 角色}), 优先级最高.
#
# 用法:
#   uv run tools/pool.py                      各层数量与待标注数
#   uv run tools/pool.py --annotate <out.html>  生成标注页(键盘快捷, 浏览器本地保存, 导出 JSON 存为 pool-overrides.json)
import json, math, os, re, sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import oklch

SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources')
OVERRIDES = os.path.join(SOURCES, 'pool-overrides.json')
FG, INHERIT = 'fg', 'inherit'

# 角色 -> (代表 scope 与取色链, 默认字体样式); 主题的角色色 = 取色链里第一个在该主题中有颜色的 scope, 都没有时退回正文
ROLES = {
    'comment': (['comment'], None),
    'string': (['string', 'string.quoted'], None),
    'regexp': (['string.regexp', 'constant.character.escape', 'string'], None),
    'escape': (['constant.character.escape', 'constant.character', 'string.regexp', 'constant.numeric'], None),
    'number': (['constant.numeric', 'constant.language', 'constant'], None),
    'constant': (['constant.language', 'constant.numeric', 'constant'], None),
    'constant_var': (['variable.other.constant', 'constant.language', 'constant.numeric'], None),
    'keyword': (['keyword', 'keyword.control', 'storage.type'], None),
    'control': (['keyword.control', 'keyword'], None),
    'operator': (['keyword.operator', FG], None),
    'storage': (['storage.type', 'storage', 'keyword'], None),
    'modifier': (['storage.modifier', 'storage', 'keyword'], None),
    'function': (['entity.name.function', 'support.function'], None),
    'builtin_fn': (['support.function', 'entity.name.function'], None),
    'type': (['entity.name.type', 'entity.name.class', 'support.class', 'support.type'], None),
    'class': (['entity.name.class', 'entity.name.type', 'support.class'], None),
    'builtin_type': (['support.type', 'support.class', 'entity.name.type'], None),
    'inherited': (['entity.other.inherited-class', 'entity.name.class', 'entity.name.type'], None),
    'namespace': (['entity.name.namespace', 'entity.name.type.namespace', 'entity.name.type.module', 'entity.name.type'], None),
    'variable': (['variable', 'variable.other.readwrite', FG], None),
    'parameter': (['variable.parameter', 'variable', FG], None),
    'this': (['variable.language', 'keyword'], None),
    'property': (['variable.other.property', 'variable.other.object.property', 'support.type.property-name', 'variable', FG], None),
    'key': (['support.type.property-name', 'meta.object-literal.key', 'variable.other.property', 'entity.other.attribute-name'], None),
    'tag': (['entity.name.tag', 'keyword'], None),
    'attribute': (['entity.other.attribute-name', 'variable.other.property', 'constant.numeric'], None),
    'heading': (['markup.heading', 'entity.name.section', 'entity.name.tag', 'keyword'], 'bold'),
    'bold': (['markup.bold'], 'bold'),
    'italic': (['markup.italic'], 'italic'),
    'quote': (['markup.quote', 'comment'], 'italic'),
    'raw': (['markup.inline.raw', 'markup.raw', 'string'], None),
    'link': (['markup.underline.link', 'string.other.link', 'constant.numeric'], None),
    'inserted': (['markup.inserted', 'string'], None),
    'deleted': (['markup.deleted', 'invalid', 'variable'], None),
    'invalid': (['invalid', 'markup.deleted'], None),
    'text': ([FG], None),
}
NAMES = dict(comment='注释', string='字符串', regexp='正则', escape='转义', number='数字', constant='常量字面量', constant_var='常量变量',
             keyword='关键字', control='流程控制', operator='运算符', storage='声明类型', modifier='修饰符', function='函数', builtin_fn='内置函数',
             type='类型', class_='类', builtin_type='内置类型', inherited='父类', namespace='命名空间', variable='变量', parameter='参数',
             this='this/self', property='属性', key='对象键', tag='标签', attribute='属性名(标签)', heading='标题', bold='粗体',
             italic='斜体', quote='引用', raw='行内代码', link='链接', inserted='新增', deleted='删除', invalid='错误', text='正文',
             inherit='跟随外层')
NAMES['class'] = '类'

# 结构规则: TextMate 命名约定 -> 角色; 选择器(后代选择器取最右一段)按最长前缀命中
STRUCT = [
    ('comment', 'comment'), ('punctuation.definition.comment', 'comment'),
    ('string', 'string'), ('string.regexp', 'regexp'), ('constant.character.escape', 'escape'), ('constant.other.placeholder', 'escape'),
    ('constant.numeric', 'number'), ('constant.language', 'constant'), ('constant.character', 'escape'), ('variable.other.constant', 'constant_var'),
    ('support.constant', 'constant'), ('constant.other', 'constant'),
    ('keyword', 'keyword'), ('keyword.control', 'control'), ('keyword.operator', 'operator'), ('keyword.other.unit', 'number'),
    ('storage', 'storage'), ('storage.type', 'storage'), ('storage.modifier', 'modifier'),
    ('entity.name.function', 'function'), ('meta.function-call', 'function'), ('support.function', 'builtin_fn'),
    ('entity.name.type', 'type'), ('entity.name.class', 'class'), ('entity.other.inherited-class', 'inherited'), ('support.type', 'builtin_type'),
    ('support.class', 'builtin_type'), ('entity.name.namespace', 'namespace'), ('entity.name.type.namespace', 'namespace'),
    ('entity.name.type.module', 'namespace'),
    ('variable', 'variable'), ('variable.parameter', 'parameter'), ('variable.language', 'this'), ('variable.other.property', 'property'),
    ('variable.other.object.property', 'property'), ('support.variable.property', 'property'), ('meta.object-literal.key', 'key'),
    ('support.type.property-name', 'key'), ('entity.name.tag', 'tag'), ('entity.other.attribute-name', 'attribute'),
    ('markup.heading', 'heading'), ('entity.name.section', 'heading'), ('markup.bold', 'bold'), ('markup.italic', 'italic'),
    ('markup.quote', 'quote'), ('markup.inline.raw', 'raw'), ('markup.raw', 'raw'), ('markup.underline.link', 'link'),
    ('string.other.link', 'link'), ('markup.inserted', 'inserted'), ('markup.deleted', 'deleted'), ('invalid', 'invalid'),
    # 跟随外层: 标点套在字符串 / 注释等里面, 包裹类 scope 覆盖整段代码, 都不应整体着色
    ('punctuation', INHERIT), ('punctuation.definition.string', 'string'), ('punctuation.definition.variable', 'variable'),
    ('punctuation.definition.tag', 'tag'), ('punctuation.definition.heading', 'heading'), ('punctuation.definition.template-expression', 'keyword'),
    ('punctuation.section.embedded', 'keyword'), ('meta', INHERIT), ('source', INHERIT), ('text', INHERIT),
    ('meta.function-call', 'function'), ('meta.object-literal.key', 'key'), ('meta.decorator', 'function'),
]
# 平票时的角色优先级: 一个原主题常把同一种颜色分给多个角色(如 One Dark 的变量, 标签, 删除同为红),
# 按颜色反推只能得到并列候选; 并列时取常见的语法角色, 少见的 markup / diff 角色排最后
PRIORITY = ['keyword', 'control', 'storage', 'modifier', 'function', 'builtin_fn', 'type', 'class', 'builtin_type', 'variable',
            'property', 'key', 'parameter', 'this', 'string', 'number', 'constant', 'constant_var', 'escape', 'regexp', 'operator',
            'tag', 'attribute', 'namespace', 'inherited', 'comment', 'text', 'raw', 'link', 'quote', 'heading', 'bold', 'italic',
            'inserted', 'deleted', 'invalid']
_rank = {r: i for i, r in enumerate(PRIORITY)}


def pick(counter: Counter, among=None) -> str:
    keys = list(among if among is not None else counter)
    return min(keys, key=lambda k: (-counter.get(k, 0), _rank.get(k, 99)))


# 常用语言排在标注页前面
LANG_ORDER = ['js', 'ts', 'tsx', 'jsx', 'json', 'python', 'html', 'css', 'scss', 'markdown', 'go', 'rust', 'java', 'c', 'cpp', 'cs',
              'php', 'ruby', 'shell', 'yaml', 'sql', 'xml', 'vue', 'less', 'lua', 'swift', 'kotlin', 'dart']


def _load(path: str) -> dict:
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', s))


def scopes_of(rule: dict) -> list[str]:
    sc = rule.get('scope') or []
    return [x.strip() for x in (sc.split(',') if isinstance(sc, str) else sc) if x.strip()]


def lookup(rules: list, scope: str, field: str = 'foreground'):
    """与 VS Code 一致: 选择器是 scope 的点分前缀即命中, 最长者胜, 同样长取后出现的(不计后代选择器)."""
    best, value = -1, None
    for r in rules:
        v = r.get('settings', {}).get(field)
        if v is None:
            continue
        for sel in scopes_of(r):
            if ' ' not in sel and (scope == sel or scope.startswith(sel + '.')) and len(sel) >= best:
                best, value = len(sel), v
    return value


def struct_role(sel: str) -> str | None:
    last = sel.split()[-1]
    best, role = -1, None
    for pre, r in STRUCT:
        if (last == pre or last.startswith(pre + '.')) and len(pre) >= best:
            best, role = len(pre), r
    return role


def _rgb(v):
    if not isinstance(v, str) or not re.fullmatch(r'#[0-9A-Fa-f]{3,8}', v):
        return None
    s = v[1:]
    s = ''.join(c * 2 for c in s) if len(s) in (3, 4) else s
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _dist(a, b) -> float:
    (L1, C1, H1), (L2, C2, H2) = oklch(a), oklch(b)
    return math.dist((L1, C1 * math.cos(H1), C1 * math.sin(H1)), (L2, C2 * math.cos(H2), C2 * math.sin(H2)))


def role_value(rules: list, role: str, fg, field: str = 'foreground'):
    chain, style = ROLES[role]
    for sc in chain:
        if sc == FG:
            return fg if field == 'foreground' else None
        v = lookup(rules, sc, field)
        if v is not None:
            return v
    return style if field == 'fontStyle' else (fg if field == 'foreground' else None)


def build(themes: list[dict]) -> dict:
    """选择器 -> {struct, cands(各原主题里颜色并列最近的候选角色集合), tier, recommended, role}."""
    from gen_vscode import source_fg
    cands = defaultdict(list)
    order = []
    for t in sorted(themes, key=lambda t: -len(_load(os.path.join(SOURCES, t['source'])).get('tokenColors', []))):
        src = _load(os.path.join(SOURCES, t['source']))
        rules = src.get('tokenColors', [])
        fg = _rgb(source_fg(src, t['dark']))
        palette = {r: c for r in ROLES if (c := _rgb(role_value(rules, r, None))) is not None}
        palette['text'] = fg
        for rule in rules:
            rgb = _rgb(rule.get('settings', {}).get('foreground'))
            if rgb is None:
                continue
            ranked = sorted(palette, key=lambda k: _dist(palette[k], rgb))
            tied = {k for k in ranked if _dist(palette[k], rgb) <= _dist(palette[ranked[0]], rgb) + 0.005}
            for sel in scopes_of(rule):
                if sel not in cands:
                    order.append(sel)
                cands[sel].append(tied)
    overrides = json.load(open(OVERRIDES, encoding='utf-8')) if os.path.exists(OVERRIDES) else {}
    pool = {}
    for sel in order:
        cs, sr = cands[sel], struct_role(sel)
        votes = Counter(k for c in cs for k in c)
        if sr == INHERIT:
            tier, rec = 0, INHERIT
        elif sr:
            other = Counter(k for c in cs if sr not in c for k in c)
            support = sum(1 for c in cs if sr in c) / len(cs)
            if other and other.most_common(1)[0][1] >= 2 and support < 0.5:
                # 结构角色的票数不低于其他角色时仍推荐结构角色, 否则推荐票数最多(并列取常见)的角色
                top = pick(other)
                tier, rec = 3, (sr if votes[sr] >= other[top] else top)
            else:
                tier, rec = 1, sr
        else:
            inter = set.intersection(*cs)
            if len(cs) >= 2 and inter:
                tier, rec = 2, pick(votes, inter)
            else:
                tier, rec = (4 if len(cs) == 1 else 5), pick(votes)
        pool[sel] = dict(struct=sr, votes=dict(votes.most_common()), themes=len(cs), tier=tier, recommended=rec,
                         role=overrides.get(sel, rec), annotated=sel in overrides)
    return pool


def lang_rank(sel: str) -> int:
    seg = sel.split()[-1].rsplit('.', 1)[-1]
    return LANG_ORDER.index(seg) + 1 if seg in LANG_ORDER else (0 if '.' not in sel or seg not in _ALL_LANGS else 99)


_ALL_LANGS = set(LANG_ORDER) | {'haskell', 'elixir', 'clojure', 'elm', 'perl', 'r', 'scala', 'groovy', 'ocaml', 'fsharp', 'erlang',
                                'powershell', 'latex', 'tex', 'coffee', 'graphql', 'toml', 'ini', 'makefile', 'dockerfile', 'sass',
                                'stylus', 'pug', 'jade', 'unison', 'asciidoc', 'diff', 'nim', 'julia', 'crystal', 'zig', 'svelte'}


def annotate(pool: dict, out: str) -> None:
    from themes import build as build_themes
    from gen_vscode import render
    previews = []
    for name in ('one-dark-fit', 'comfort-dracula', 'one-light-fit', 'comfort-github-light'):
        t = next(x for x in build_themes() if x['name'] == name)
        g = render(t)
        roles = {r: role_value(g['tokenColors'], r, g['colors']['editor.foreground']) for r in ROLES}
        roles[INHERIT] = g['colors']['editor.foreground']
        previews.append(dict(name=t['label'], bg=g['colors']['editor.background'], fg=g['colors']['editor.foreground'], roles=roles))
    items = [dict(scope=s, **{k: v for k, v in p.items() if k != 'annotated'}) for s, p in pool.items() if p['tier'] >= 3]
    items.sort(key=lambda x: (lang_rank(x['scope']), -x['themes'], x['tier'], x['scope']))
    data = dict(items=items, previews=previews, names=NAMES, roles=list(ROLES) + [INHERIT],
                annotated=json.load(open(OVERRIDES, encoding='utf-8')) if os.path.exists(OVERRIDES) else {})
    html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pool-annotate.html'), encoding='utf-8').read()
    open(out, 'w', encoding='utf-8').write(html.replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False)))
    print(f'标注页已写入 {out}: 待标注 {len(items)} 个; 导出的 JSON 存为 {os.path.relpath(OVERRIDES)}')


def main() -> int:
    from themes import build as build_themes
    pool = build(build_themes())
    if '--annotate' in sys.argv:
        annotate(pool, sys.argv[sys.argv.index('--annotate') + 1])
        return 0
    tiers = Counter(p['tier'] for p in pool.values())
    names = {0: '跟随外层', 1: '结构规则', 2: '原主题候选交集', 3: '结构规则被多数反对', 4: '仅一个原主题', 5: '原主题分歧'}
    print(f'规则池 {len(pool)} 个选择器')
    for k in sorted(tiers):
        print(f'  {k} {names[k]}: {tiers[k]}')
    todo = sum(1 for p in pool.values() if p['tier'] >= 3 and not p['annotated'])
    print(f'待人工标注 {todo} 个(未标注时用推荐值); 已标注 {sum(p["annotated"] for p in pool.values())} 个')
    return 0


if __name__ == '__main__':
    sys.exit(main())
