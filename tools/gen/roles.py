# /// script
# requires-python = ">=3.11"
# ///
# 语法角色差异化标准: 由参照主题(assets/layers/reference.json)按用户定的规则给每对语法角色定"分开 / 可同色", 写出 assets/layers/roles.json(勿手改).
# 规则(用户定):
#   1 共识: 参照家族里明显不同(ΔE >= APART_DE)的占比 >= SHOULD 的对(原"必须分开" >= MUST 与"应该分开")一律分开
#   2 其余对(原"设计自由"与"惯例同色")只看前 5 名主题: 至少 TOP_MAJORITY 家明显不同才分开, 否则可同色
#   前 5 名 = 参照家族代表变体在案例集上按规则 1 的撞色数从少到多排序的前 TOP 个
# 判定(案例集 assets/layers/cases.json): 一个案例里同时出现的两类要分开的角色, 各随机取一个 token, 渲染色 ΔE < APART_DE 的概率 >= COLLIDE 即撞色;
#   前 5 名里至少 TOP_MAJORITY 家在同一案例也撞色的(案例, 角色对)豁免(最好的主题都这样做, 多是语法分词的口径);
#   门禁线 gate = 前 5 名在最终标准下撞色数的中位数.
# 用法: uv run tools/gen/roles.py                  按 reference.json 与命中表重写 roles.json
#       uv run tools/gen/roles.py --ref <主题目录>  重算 reference.json(目录里是展开好的主题 JSON: name / type / colors / tokenColors;
#                                                  需要本机 VS Code 的语法分词), 再重写 roles.json; 案例集变了也要重跑
import itertools, json, os, re, statistics, subprocess, sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', d) for d in ('lib', 'gen')]
import pool
from colorlib import de2000, h

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LAYERS = os.path.join(ROOT, 'assets', 'layers')
REFERENCE = os.path.join(LAYERS, 'reference.json')
CASES = os.path.join(LAYERS, 'cases.json')
OUT = os.path.join(LAYERS, 'roles.json')
APART_DE, SAME_DE = 10.0, 5.0
MUST, SHOULD, SAME = 0.9, 0.75, 0.5
TOP, TOP_MAJORITY = 5, 3
COLLIDE = 0.25
# 标准里的角色(取色链见 pool.ROLES); text 是正文色
ROLES = ['keyword', 'operator', 'storage', 'function', 'builtin_fn', 'type', 'builtin_type', 'namespace', 'string', 'regexp', 'escape',
         'number', 'constant', 'constant_var', 'variable', 'parameter', 'property', 'key', 'tag', 'attribute', 'this', 'comment', 'text',
         'heading', 'link', 'raw']
# 分词判出的其余角色归到标准角色; 不在表里且不在 ROLES 里的(diff 增删, 错误标记)不参与判定
CANON = {'control': 'keyword', 'modifier': 'storage', 'class': 'type', 'inherited': 'type', 'prop_name': 'key', 'quote': 'comment',
         'bold': 'text', 'italic': 'text'}


def canon(r: str) -> str | None:
    r = CANON.get(r, r)
    return r if r in ROLES else None


def pair_key(a: str, b: str) -> str:
    i, j = sorted((ROLES.index(a), ROLES.index(b)))
    return f'{ROLES[i]}|{ROLES[j]}'


def role(scopes: list[str]) -> str:
    """token 的语义角色: scope 链由内向外第一个能按命名约定判出角色(不是跟随外层)的."""
    for s in reversed(scopes[1:]):
        r = pool.struct_role(s)
        if r and r != pool.INHERIT:
            return r
    return 'text'


def role_colors(theme: dict) -> dict[str, str]:
    fg = pool.norm_hex((theme.get('colors') or {}).get('editor.foreground')) or ('#D4D4D4' if theme.get('dark') else '#333333')
    out = {}
    for r in ROLES:
        v = fg if r == 'text' else pool.norm_hex(pool.role_value(theme.get('tokenColors', []), r, fg))
        out[r] = (v or fg)[:7]
    return out


def case_files() -> list[str]:
    return list(json.load(open(CASES, encoding='utf-8'))['cases'])


_de = {}


def de(a: str, b: str) -> float:
    k = (a, b) if a < b else (b, a)
    if k not in _de:
        _de[k] = de2000(h(a[1:]), h(b[1:]))
    return _de[k]


def checks(tokens: list, separate: set[str], exempt: set[str]) -> list[tuple]:
    """由 [案例序号, 行号, 角色] 列出要核对的 (案例序号, 角色对, a 的 token 下标, b 的 token 下标); 豁免项以 "<案例路径>@<角色对>" 记."""
    files = case_files()
    by = defaultdict(lambda: defaultdict(list))
    for k, (f, _, r) in enumerate(tokens):
        if (c := canon(r)) is not None:
            by[f][c].append(k)
    out = []
    for f, rs in sorted(by.items()):
        names = sorted(rs, key=ROLES.index)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                k = f'{a}|{b}'
                if k in separate and f'{files[f]}@{k}' not in exempt:
                    out.append((f, k, rs[a], rs[b]))
    return out


def weight(colors: list[str], ta: list[int], tb: list[int]) -> float:
    """各随机取一个 token, 渲染色分不开(ΔE < APART_DE)的概率."""
    ca, cb = Counter(colors[i] for i in ta), Counter(colors[i] for i in tb)
    return sum(na * nb for x, na in ca.items() for y, nb in cb.items() if de(x, y) < APART_DE) / (len(ta) * len(tb))


def judge(colors: list[str], checks_: list[tuple]) -> dict:
    """n: 撞色的 (案例, 角色对) 数; w: 撞色概率之和(贪心用); bad: 撞色清单 [(案例序号, 角色对)]."""
    ws = [weight(colors, ta, tb) for _, _, ta, tb in checks_]
    bad = [(c[0], c[1]) for c, w in zip(checks_, ws) if w >= COLLIDE]
    return dict(n=len(bad), w=sum(ws), bad=bad, ws=ws)


def tokenize(theme_dir: str) -> dict[str, tuple[list, list]]:
    """主题目录里每个主题(文件名去 .json)在案例集上的 ([案例序号, 行号, 角色], 颜色)."""
    files = [os.path.join(ROOT, f) for f in case_files()]
    p = subprocess.run(['node', os.path.join(ROOT, 'tools', 'textmate', 'tokenize.mjs'), theme_dir, *files], capture_output=True, text=True,
                       cwd=ROOT, timeout=900)
    if p.returncode:
        raise SystemExit(p.stderr.strip()[-2000:])
    out = {}
    for name, t in json.loads(p.stdout).items():
        tokens, colors = [], []
        for fi, f in enumerate(files):
            for k in t['files'][os.path.basename(f)]:
                if re.search(r'\w', k['text']):
                    tokens.append([fi, k['ln'], role(k['scopes'])])
                    colors.append(pool.norm_hex(k['color'])[:7])
        out[name] = (tokens, colors)
    return out


def consensus(fams: dict) -> dict[str, dict]:
    """每对角色在全部参照家族里明显不同 / 同色的占比与原分级."""
    out = {}
    for a, b in itertools.combinations(ROLES, 2):
        ds = [de(f['roles'][a], f['roles'][b]) for f in fams.values()]
        apart, same = sum(d >= APART_DE for d in ds) / len(ds), sum(d < SAME_DE for d in ds) / len(ds)
        auto = '惯例同色' if same >= SAME else '必须分开' if apart >= MUST else '应该分开' if apart >= SHOULD else '设计自由'
        out[pair_key(a, b)] = dict(apart=round(apart, 3), same=round(same, 3), auto=auto)
    return out


def refresh_reference(theme_dir: str) -> None:
    """每个主题家族(文件名去扩展名后的第一段)取文件名排序第一个变体, 一家一票; 排前 5 名, 定豁免与门禁线."""
    reps = {}
    for f in sorted(os.listdir(theme_dir)):
        if f.endswith('.json'):
            reps.setdefault(f[:-5].split('_')[0], f)
    fams = {}
    for key, f in reps.items():
        t = pool._load(os.path.join(theme_dir, f))
        fams[key] = dict(file=f, name=t.get('name'), bg=(pool.norm_hex(t['colors'].get('editor.background')) or '#808080')[:7], roles=role_colors(t))
    cons = consensus(fams)
    tok = tokenize(theme_dir)
    base = {k for k, v in cons.items() if v['auto'] in ('必须分开', '应该分开')}
    base_all = {k: judge(tok[reps[k][:-5]][1], checks(tok[reps[k][:-5]][0], base, set()))['n'] for k in fams}
    ranked = sorted(fams, key=base_all.__getitem__)
    base_n = {k: base_all[k] for k in ranked}
    top = ranked[:TOP]
    final = base | {k for k, v in cons.items() if k not in base and sum(de(fams[t]['roles'][k.split('|')[0]], fams[t]['roles'][k.split('|')[1]]) >= APART_DE
                                                                       for t in top) >= TOP_MAJORITY}
    files = case_files()
    votes = Counter()
    for t in top:
        tokens, colors = tok[reps[t][:-5]]
        for f, k in judge(colors, checks(tokens, final, set()))['bad']:
            votes[f'{files[f]}@{k}'] += 1
    exempt = sorted(k for k, v in votes.items() if v >= TOP_MAJORITY)
    top_n = {t: judge(tok[reps[t][:-5]][1], checks(tok[reps[t][:-5]][0], final, set(exempt)))['n'] for t in top}
    data = dict(about='参照主题家族(tools/gen/roles.py --ref 生成, 勿手改): Open VSX 头部主题扩展的全部变体 + VS Code 内置主题, 按家族去重, 一家一票',
                families=fams, rank=base_n, top=top, exempt=exempt, topViolations=top_n, gate=statistics.median(top_n.values()))
    open(REFERENCE, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    print(f'reference.json: {len(fams)} 个家族; 前 {TOP} 名 ' + ', '.join(f'{t} {top_n[t]}' for t in top) + f'; 豁免 {len(exempt)} 项; 门禁线 {data["gate"]}')


def case_roles() -> dict[str, set[str]]:
    """案例 -> 其中出现的标准角色, 按命中表的 token 角色."""
    hits = json.load(open(os.path.join(LAYERS, 'hits.json'), encoding='utf-8'))
    out = {f: set() for f in hits['files']}
    for fi, _, r in hits['tokens']:
        if (c := canon(r)) is not None:
            out[hits['files'][fi]].add(c)
    return out


def build() -> dict:
    ref = json.load(open(REFERENCE, encoding='utf-8'))
    fams, top = ref['families'], ref['top']
    present = case_roles()
    pairs = {}
    for k, c in consensus(fams).items():
        a, b = k.split('|')
        top_apart = sum(de(fams[t]['roles'][a], fams[t]['roles'][b]) >= APART_DE for t in top)
        if c['auto'] in ('必须分开', '应该分开'):
            grade, why = '分开', f"{c['apart']:.0%} 的参照家族明显不同(规则 1)"
        elif top_apart >= TOP_MAJORITY:
            grade, why = '分开', f"原为{c['auto']}, 前 {TOP} 名里 {top_apart} 家明显不同(规则 2)"
        else:
            grade, why = '可同色', f"原为{c['auto']}, 前 {TOP} 名里只有 {top_apart} 家明显不同(规则 2)"
        pairs[k] = dict(c, topApart=top_apart, grade=grade, why=why, cases=sorted(f for f, rs in present.items() if a in rs and b in rs))
    return dict(about='语法角色差异化标准(tools/gen/roles.py 生成, 勿手改)',
                rules=dict(apartDE=APART_DE, sameDE=SAME_DE, must=MUST, should=SHOULD, same=SAME, collide=COLLIDE, top=top,
                           topMajority=TOP_MAJORITY, families=len(fams), gate=ref['gate']),
                roles=[dict(id=r, name=pool.NAMES.get(r, r)) for r in ROLES], exempt=ref['exempt'], pairs=pairs)


def separate_set(std: dict) -> set[str]:
    return {k for k, p in std['pairs'].items() if p['grade'] == '分开'}


def write() -> None:
    data = build()
    open(OUT, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=1) + '\n')
    n = Counter(p['grade'] for p in data['pairs'].values())
    print(f"roles.json: 分开 {n['分开']}(其中按前 {TOP} 名补入 {sum(p['grade'] == '分开' and p['auto'] in ('设计自由', '惯例同色') for p in data['pairs'].values())}), "
          f"可同色 {n['可同色']}; 豁免 {len(data['exempt'])} 项; 门禁线 {data['rules']['gate']}")


def main() -> int:
    if '--ref' in sys.argv:
        refresh_reference(os.path.abspath(sys.argv[sys.argv.index('--ref') + 1]))
    write()
    return 0


if __name__ == '__main__':
    sys.exit(main())
