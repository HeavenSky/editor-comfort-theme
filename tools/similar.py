# /// script
# requires-python = ">=3.11"
# ///
# 主题配色接近度检测: 逐项比对 VS Code 颜色主题, 找出"整体接近, 只有少数几处差别大"的可合并主题对,
# 把差别大的地方按 (A 色, B 色) 归组, 再按底色聚成几处供选择, 并可按选择生成合并预览、跑一遍门禁.
#
# 用法:
#   uv run tools/similar.py <a.json> <b.json> [更多...]         两两比对; 两个以上时先给接近度矩阵
#   uv run tools/similar.py a.json b.json --merge out.json [--take 1,3]
#       以 a 为底生成合并预览: --take 列出的差异组改用 b 的颜色, 其余保持 a; 输出后跑 清晰/护眼/柔和/防疲劳 评级.
#
# 比对项: colors 全部键(半透明色叠到各自编辑区底上), tokenColors 按 scope 展开(同 scope 取最后一条),
# semanticTokenColors. 色差用 CIEDE2000: < 3 视为单独看无法分辨, >= 5 视为明显差异.
import json, os, re, sys
from collections import defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import blend, de2000, h
from schema import registry

REGISTRY = registry()['colors']

NEAR = 3.0          # 单独看无法分辨(并排时 2~3 仍可能察觉)
DISTINCT = 5.0      # 明显差异, 归入差异组
# 可合并: 难辨项占比够高, 且明显差异只集中在少数几组
MERGE_NEAR_SHARE = 0.80
# 难辨占比稍低(多半是正文一类覆盖面广的颜色差了 3~5), 其余条件满足时列为"可考虑合并", 由人看差异组决定
CONSIDER_NEAR_SHARE = 0.60
MERGE_MAX_GROUPS = 6
CONSIDER_MAX_GROUPS = 10
# 差异组按底色聚类: A 侧与 B 侧的不透明色都在这个色差内即视为同一处选择(例如同一个终端黄派生出的图标, 高亮, 边框)
CLUSTER_DE = 8.0
# 编辑区主体: 这些项任何一个明显不同, 两主题写代码时的观感就不同, 不建议合并
CORE = ['editor.background', 'editor.foreground', 'token:comment', 'token:keyword', 'token:string', 'token:entity.name.function',
        'token:variable', 'token:entity.name.type', 'token:constant.numeric', 'editor.selectionBackground']


def load(path: str) -> dict:
    return json.loads(re.sub(r'^\s*//.*$', '', open(path, encoding='utf-8').read(), flags=re.M))


def parse(v, under):
    if not isinstance(v, str) or not v.startswith('#'):
        return None
    s = v.lstrip('#')
    if len(s) in (3, 4):
        s = ''.join(ch * 2 for ch in s)
    if len(s) not in (6, 8):
        return None
    c = h(s[:6])
    return blend(c, under, int(s[6:8], 16) / 255) if len(s) == 8 else c


def items(t: dict) -> dict:
    """主题里可比对的颜色项: 键 -> (原始值, 叠底后的 RGB)."""
    c = t['colors']
    bg = parse(c['editor.background'], (0, 0, 0))
    out = {}
    for k, v in c.items():
        info = REGISTRY.get(k)
        if info is None or info.get('deprecated'):
            continue  # 未注册或已废弃的键 VS Code 不生效, 不参与比对
        rgb = parse(v, bg)
        if rgb:
            out[k] = (v, rgb)
    for r in t.get('tokenColors', []):
        fg = r.get('settings', {}).get('foreground')
        rgb = parse(fg, bg)
        if not rgb:
            continue
        scopes = r.get('scope') or []
        for sc in scopes if isinstance(scopes, list) else [scopes]:
            for s in str(sc).split(','):
                if s.strip():
                    out['token:' + s.strip()] = (fg, rgb)
    for k, v in (t.get('semanticTokenColors') or {}).items():
        fg = v if isinstance(v, str) else v.get('foreground')
        rgb = parse(fg, bg)
        if rgb:
            out['semantic:' + k] = (fg, rgb)
    return out


def compare(a: dict, b: dict) -> dict:
    ia, ib = items(a), items(b)
    common = sorted(set(ia) & set(ib))
    diffs = {k: de2000(ia[k][1], ib[k][1]) for k in common}
    groups = defaultdict(list)
    for k, d in diffs.items():
        if d >= DISTINCT:
            groups[(ia[k][0].upper(), ib[k][0].upper())].append(k)
    ranked = sorted(groups.items(), key=lambda g: (-max(diffs[k] for k in g[1]), g[0]))
    opaque = lambda v: h(v.lstrip('#')[:6])
    clusters = []
    for (ca, cb), keys in ranked:
        for cl in clusters:
            if de2000(opaque(ca), opaque(cl['a'])) < CLUSTER_DE and de2000(opaque(cb), opaque(cl['b'])) < CLUSTER_DE:
                cl['keys'] += keys
                cl['pairs'].append((ca, cb))
                break
        else:
            clusters.append(dict(a=ca, b=cb, keys=list(keys), pairs=[(ca, cb)]))
    near = sum(d < NEAR for d in diffs.values()) / len(diffs) if diffs else 0
    core = {k: diffs[k] for k in CORE if k in diffs}
    core_ok = all(d < DISTINCT for d in core.values())
    if core_ok and len(clusters) <= MERGE_MAX_GROUPS and near >= MERGE_NEAR_SHARE:
        status = 'merge'
    elif core_ok and len(clusters) <= CONSIDER_MAX_GROUPS and near >= CONSIDER_NEAR_SHARE:
        status = 'consider'
    else:
        status = 'no'
    return dict(n=len(diffs), only_a=len(set(ia) - set(ib)), only_b=len(set(ib) - set(ia)), near=near,
                distinct=sum(d >= DISTINCT for d in diffs.values()), mean=sum(diffs.values()) / len(diffs) if diffs else 0,
                core=core, core_ok=core_ok, groups=[((cl['a'], cl['b']), cl['keys'], max(diffs[k] for k in cl['keys'])) for cl in clusters],
                status=status, diffs=diffs)


def name_of(path: str) -> str:
    return re.sub(r'(-color-theme)?\.json$', '', os.path.basename(path))


def report(pa: str, pb: str, r: dict) -> None:
    print(f'\n== {name_of(pa)}  vs  {name_of(pb)}')
    print(f"  共同项 {r['n']} (仅 A {r['only_a']}, 仅 B {r['only_b']}); 难辨(ΔE<{NEAR:g}) {r['near']:.0%}; "
          f"明显差异(ΔE>={DISTINCT:g}) {r['distinct']} 项 / {len(r['groups'])} 处; 平均 ΔE {r['mean']:.2f}")
    core = ', '.join(f"{k.replace('token:', '')} {d:.1f}" for k, d in r['core'].items())
    print(f"  编辑区主体 ΔE: {core}")
    if r['status'] == 'merge':
        verdict = '可合并: 整体接近, 差异只集中在下列几组, 选定后合并'
    elif r['status'] == 'consider':
        mid = sum(NEAR <= d < DISTINCT for d in r['diffs'].values())
        verdict = f'可考虑合并: 编辑区主体无明显差异, 但有 {mid} 项落在 ΔE {NEAR:g}~{DISTINCT:g}(并排可见), 看完下列差异组再定'
    elif not r['core_ok']:
        verdict = '不建议合并: 编辑区主体颜色明显不同'
    else:
        verdict = '不建议合并: 差异面太广'
    print(f'  结论: {verdict}')
    for i, ((ca, cb), keys, d) in enumerate(r['groups'][:20], 1):
        shown = ', '.join(k.replace('token:', '') for k in keys[:4]) + (f' 等 {len(keys)} 项' if len(keys) > 4 else '')
        print(f'  [{i}] ΔE {d:5.1f}  A {ca:>9}  B {cb:>9}  {shown}')
    if len(r['groups']) > 20:
        print(f"  ... 另有 {len(r['groups']) - 20} 组未列出")


def merge(pa: str, pb: str, r: dict, take: set[int], out: str) -> None:
    """以 A 为底, 把选中差异组里的键换成 B 的原始值(含 tokenColors 里对应 scope 的规则)."""
    a, b = load(pa), load(pb)
    ib = items(b)
    chosen = {k for i, (_, keys, _) in enumerate(r['groups'], 1) if i in take for k in keys}
    for k in chosen:
        if k.startswith('token:'):
            scope = k[len('token:'):]
            for rule in a.get('tokenColors', []):
                scopes = rule.get('scope') or []
                flat = [s.strip() for sc in (scopes if isinstance(scopes, list) else [scopes]) for s in str(sc).split(',')]
                if scope in flat and 'foreground' in rule.get('settings', {}):
                    rule['settings']['foreground'] = ib[k][0]
        elif k.startswith('semantic:'):
            key = k[len('semantic:'):]
            v = a['semanticTokenColors'][key]
            a['semanticTokenColors'][key] = ib[k][0] if isinstance(v, str) else {**v, 'foreground': ib[k][0]}
        else:
            a['colors'][k] = ib[k][0]
    a['name'] = f"{a.get('name', name_of(pa))} (merged)"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(a, f, ensure_ascii=False, indent='\t')
    print(f'\n合并预览已写入 {out}: 底 {name_of(pa)}, 取 {name_of(pb)} 的差异组 {sorted(take) or "无"} 共 {len(chosen)} 项')
    from metrics import from_vscode, grade
    from comfort import rate
    m = from_vscode(out)
    clear, eye, why = grade(m)
    rr = rate(m)
    print(f"门禁: 清晰 {clear}, 护眼 {eye}, 柔和 {rr['soft']['score']}{'' if rr['soft']['ok'] else ' ×'}, "
          f"防疲劳 {rr['fatigue']['score']}{'' if rr['fatigue']['ok'] else ' ×'}")
    for w in why + [f'柔和: {x}' for x in rr['soft']['why']] + [f'防疲劳: {x}' for x in rr['fatigue']['why']]:
        print(f'  - {w}')


def main() -> int:
    args = sys.argv[1:]
    out = take = None
    if '--merge' in args:
        i = args.index('--merge')
        out = args[i + 1]
        del args[i:i + 2]
    if '--take' in args:
        i = args.index('--take')
        take = {int(x) for x in args[i + 1].split(',') if x}
        del args[i:i + 2]
    files = [a for a in args if not a.startswith('--')]
    if len(files) < 2:
        print('用法: uv run tools/similar.py <a.json> <b.json> [更多...] [--merge out.json [--take 1,2]]')
        return 2
    themes = {f: load(f) for f in files}
    pairs = [(x, y) for i, x in enumerate(files) for y in files[i + 1:]]
    results = {p: compare(themes[p[0]], themes[p[1]]) for p in pairs}
    if len(files) > 2:
        print('接近度矩阵(难辨项占比 / 明显差异处数; * 可合并, ? 可考虑合并):')
        for x, y in sorted(pairs, key=lambda p: -results[p]['near']):
            r = results[(x, y)]
            mark = {'merge': ' *', 'consider': ' ?'}.get(r['status'], '')
            print(f"  {name_of(x):26} {name_of(y):26} {r['near']:4.0%} / {len(r['groups']):3}{mark}")
        pairs = [p for p in pairs if results[p]['status'] != 'no']
    for p in pairs:
        report(*p, results[p])
    if out:
        if len(files) != 2:
            print('--merge 只支持两个主题')
            return 2
        merge(files[0], files[1], results[(files[0], files[1])], take or set(), out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
