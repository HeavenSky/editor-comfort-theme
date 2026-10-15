# /// script
# requires-python = ">=3.11"
# ///
# 撞色检查, 三种口径:
#   默认         逐主题列出调色带来的新撞色: 两个不同族角色(pool.FAMILY)生成后 ΔE < CLASH, 而原主题里 ΔE >= APART
#   --grammars   按 VS Code 内置的每个语法文件: 取语法里出现的全部 scope, 按各主题解析到的规则组算同样的新撞色, 汇总涉及的语法数
#   --markdown   按真实分词着色(tools/textmate/tokenize.mjs)检查 Markdown 文件里各语义类(标题, 正文, 列表符, 粗体, 斜体, 代码, 链接, 引用)的色差;
#                低于 SEPARATE_DE 判撞色(退出码 1), 再高 2 以内只提示偏近
# 色差一律是 CIEDE2000. 只报告不改色: 撞色若来自调色步骤, 关掉对应步骤(tools/gen/steps.py)即可还原原主题.
# 用法: uv run tools/check/clash.py [主题名过滤...]
#       uv run tools/check/clash.py --grammars [VS Code 扩展目录]
#       uv run tools/check/clash.py --markdown [file.md]   (默认 tools/samples/sample.md; 需先 npm ci 装好 vscode-textmate)
import glob, json, os, subprocess, sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', d) for d in ('lib', 'gen', 'check', 'lab')]
import pool
from colorlib import cr, de2000, h
from gen_vscode import load, source_fg

# Markdown 专用角色(文档里挨着出现, 与代码角色不同屏); 两色 ΔE 低于 SEPARATE_DE 时肉眼难分
MARKDOWN_ROLES = ['heading', 'link', 'raw', 'quote', 'bold', 'italic']
SEPARATE_DE = 6.0
from themes import build

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
THEMES = os.path.join(ROOT, 'themes')
CLASH, APART = 5.0, 10.0
EXT = os.path.join(os.environ.get('VSCODE_APP', '/Applications/Visual Studio Code.app'), 'Contents/Resources/app/extensions')


def theme_file(name: str) -> str:
    return os.path.join(THEMES, f'{name}.json')


def source_roles(t: dict) -> dict:
    """原主题里各角色的颜色; 派生角色(variable, prop_name, X muted)按其基础角色算."""
    src = load(os.path.join(pool.SOURCES, t['source']))
    fg = source_fg(src, t['dark'])
    roles = {r: pool._rgb(pool.role_value(src.get('tokenColors', []), r, fg)) for r in pool.ROLES}
    roles['prop_name'] = roles.get('storage')
    return roles


def apart(a: str, b: str) -> bool:
    """不同族, 且同属代码或同属 Markdown 文档(两个领域的角色不会同屏, 文档内部见 --markdown)."""
    ra, rb = a.split()[0], b.split()[0]
    return ra != rb and pool.FAMILY.get(ra, ra) != pool.FAMILY.get(rb, rb) and (ra in MARKDOWN_ROLES) == (rb in MARKDOWN_ROLES)


def by_theme(only: list[str]) -> int:
    total = 0
    for t in build():
        if only and not any(o in t['name'] for o in only):
            continue
        th = json.load(open(theme_file(t['name']), encoding='utf-8'))
        sr = source_roles(t)
        g = {r['name'][8:]: h(r['settings']['foreground'][1:7]) for r in th['tokenColors']
             if r.get('name', '').startswith('Comfort ') and 'foreground' in r['settings']}
        ks, out = sorted(g), []
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                sa, sb = sr.get(a.split()[0]), sr.get(b.split()[0])
                if not (apart(a, b) and sa and sb):
                    continue
                d, d0 = de2000(g[a], g[b]), de2000(sa, sb)
                if d < CLASH and d0 >= APART:
                    out.append(f'{a}~{b} {d0:.0f}->{d:.1f}')
        total += len(out)
        print(f"{t['name']:13} {len(out):3}  {'; '.join(out)}")
    print(f'\n调色带来的新撞色共 {total} 对(生成后 ΔE < {CLASH}, 原主题 ΔE >= {APART})')
    return 0


def grammar_scopes(node, out: set) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('name', 'contentName') and isinstance(v, str):
                out.update(x for x in v.split() if '$' not in x)
            else:
                grammar_scopes(v, out)
    elif isinstance(node, list):
        for v in node:
            grammar_scopes(v, out)


def resolver(theme: dict):
    """与 VS Code 一样按点分前缀匹配, 最长者胜, 同长取后者; 后代选择器依赖上下文, 不计."""
    rules = []
    for i, r in enumerate(theme['tokenColors']):
        sc = r.get('scope') or []
        for sel in (sc.split(',') if isinstance(sc, str) else sc):
            sel = sel.strip()
            if sel and ' ' not in sel and 'foreground' in r['settings']:
                rules.append((sel, i, r.get('name', ''), r['settings']['foreground']))

    def resolve(scope):
        best = None
        for sel, i, name, fg in rules:
            if (scope == sel or scope.startswith(sel + '.')) and (best is None or (len(sel), i) >= (len(best[0]), best[1])):
                best = (sel, i, name, fg)
        return best
    return resolve


def by_grammar(ext: str) -> int:
    grammars = {}
    for f in sorted(glob.glob(os.path.join(ext, '*/syntaxes/*.json'))):
        try:
            g = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        out = set()
        grammar_scopes(g, out)
        grammars[os.path.basename(f).replace('.tmLanguage.json', '')] = out
    if not grammars:
        print(f'没找到语法文件: {ext}')
        return 2
    themes = {t['name']: (json.load(open(theme_file(t['name']), encoding='utf-8')), source_roles(t)) for t in build()}
    report = defaultdict(lambda: defaultdict(set))
    for gname, scs in grammars.items():
        for tname, (th, sr) in themes.items():
            resolve = resolver(th)
            colors = {}
            for sc in scs:
                b = resolve(sc)
                if b and b[2].startswith('Comfort '):
                    colors[b[2][8:]] = b[3]
            ks = sorted(colors)
            for i, a in enumerate(ks):
                for b in ks[i + 1:]:
                    sa, sb = sr.get(a.split()[0]), sr.get(b.split()[0])
                    if apart(a, b) and sa and sb and de2000(h(colors[a][1:7]), h(colors[b][1:7])) < CLASH and de2000(sa, sb) >= APART:
                        report[(a, b)][tname].add(gname)
    print(f'{len(grammars)} 个语法文件; 调色带来的新撞色(角色对: 主题 x 涉及语法数):')
    for (a, b), per in sorted(report.items(), key=lambda x: -sum(len(v) for v in x[1].values())):
        print(f"  {a} ~ {b}: " + ', '.join(f'{t} {len(g)}' for t, g in sorted(per.items())))
    if not report:
        print('  无')
    return 0


MD_CLASSES = [('标题', ['markup.heading', 'entity.name.section']), ('列表符', ['punctuation.definition.list.begin']), ('粗体', ['markup.bold']),
              ('斜体', ['markup.italic']), ('代码', ['markup.inline.raw']), ('链接字', ['string.other.link']), ('网址', ['markup.underline.link']),
              ('引用', ['markup.quote'])]
# 同一类东西同色可接受: 标题与它的列表符号(暗彩), 链接文字与网址, 粗体与斜体(靠字形区分), 正文与粗体 / 斜体(常用正文色)
MD_SAME_OK = {frozenset(p) for p in [('标题', '列表符'), ('链接字', '网址'), ('粗体', '斜体'), ('正文', '粗体'), ('正文', '斜体')]}


def md_class(scopes: list[str]) -> str | None:
    s = ' '.join(scopes)
    for k, keys in MD_CLASSES:
        if any(x in s for x in keys):
            return k
    return None if 'punctuation' in scopes[-1] else '正文'


def by_markdown(md: str) -> int:
    run = subprocess.run(['node', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'textmate', 'tokenize.mjs'), THEMES, md],
                         capture_output=True, text=True)
    if run.returncode:
        print(run.stderr.strip() or 'tokenize.mjs 失败; 先 npm ci 安装 vscode-textmate / vscode-oniguruma')
        return 2
    bad_total = 0
    for name, th in json.loads(run.stdout).items():
        bg, col = h(th['bg'][1:7]), {}
        for t in th['files'][os.path.basename(md)]:
            k = md_class(t['scopes'])
            if k:
                col.setdefault(k, Counter())[(t['color'].upper(), t['bold'])] += 1
        c = {k: v.most_common(1)[0][0] for k, v in col.items()}
        ks, bad, near = list(c), [], []
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                de = de2000(h(c[a][0][1:7]), h(c[b][0][1:7]))
                if frozenset((a, b)) in MD_SAME_OK:
                    continue
                if de < SEPARATE_DE:
                    bad.append(f'{a}~{b} {de:.1f}')
                elif de < SEPARATE_DE + 2:
                    near.append(f'{a}~{b} {de:.1f}')
        bad_total += len(bad)
        print(name.ljust(13), ' '.join(f"{k}{v[0]}{'粗' if v[1] else ''}({cr(h(v[0][1:7]), bg):.1f})" for k, v in c.items()))
        print(' ' * 14, f'撞色(ΔE < {SEPARATE_DE:g}):', '; '.join(bad) or '无', f'| 偏近(< {SEPARATE_DE + 2:g}):', '; '.join(near) or '无')
    return 1 if bad_total else 0


def main() -> int:
    args = sys.argv[1:]
    if '--grammars' in args:
        rest = [a for a in args if a != '--grammars']
        return by_grammar(rest[0] if rest else EXT)
    if '--markdown' in args:
        rest = [a for a in args if a != '--markdown']
        return by_markdown(os.path.abspath(rest[0] if rest else os.path.join(ROOT, 'tools/samples/sample.md')))
    return by_theme(args)


if __name__ == '__main__':
    sys.exit(main())
