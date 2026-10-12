# /// script
# requires-python = ">=3.11"
# ///
# 规则池观感审计: 每个选择器在原主题里的实际观感(灰白 / 彩色, 暗淡 / 明亮, 加粗, 斜体) 对照 生成后各主题的观感, 找出
#   R1: 原主题有意压暗(弱化), 生成后却明亮或加粗;
#   R2: 人工标注的选择器原本是灰白, 生成后成了明亮或加粗的彩色;
#   加粗: 生成后加粗而原主题没有.
# 只采信原主题里显式写出该选择器的规则, 靠前缀继承的不算证据; 暗淡与灰白的口径与 pool.MUTED_* 一致.
# 修正方式见 pool.py 的暗彩(muted)判据与标注里的 "<角色> muted".
# 用法: uv run tools/pool_audit.py [--all] [--json out.json]   (默认只看人工标注; --all 看整个规则池)
import json, math, os, re, sys
from collections import Counter

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
import pool
from colorlib import cr, h, oklch
from gen_vscode import source_fg
from themes import build

NEUTRAL, DIM_REL, DIM_ABS, DIM_HUE = pool.MUTED_NEUTRAL, pool.MUTED_REL, pool.MUTED_ABS, pool.MUTED_HUE
NAMED = {'white': '#FFFFFF', 'black': '#000000'}


def rgb(c):
    c = NAMED.get(str(c).lower(), c)
    if not isinstance(c, str) or not re.fullmatch(r'#[0-9A-Fa-f]{3,8}', c):
        return None
    s = c[1:]
    return h(''.join(x * 2 for x in s[:3]) if len(s) in (3, 4) else s[:6])


def exact(rules, sel, field):
    v = None
    for r in rules:
        if sel in pool.scopes_of(r) and r.get('settings', {}).get(field) is not None:
            v = r['settings'][field]
    return v


def sources():
    seen, out = set(), []
    for t in build():
        src = pool._load(os.path.join(pool.SOURCES, t['source']))
        rules = src.get('tokenColors', [])
        shape = tuple(tuple(pool.scopes_of(r)) for r in rules)
        if shape in seen:
            continue
        seen.add(shape)
        bg, fg = rgb(src['colors']['editor.background']), rgb(source_fg(src, t['dark']))
        crs = sorted(cr(c, bg) for r in rules if (c := rgb(r.get('settings', {}).get('foreground'))))
        out.append(dict(name=t['name'], rules=rules, bg=bg, fg=fg, med=crs[len(crs) // 2]))
    return out


def src_look(s, sel, role):
    c = rgb(exact(s['rules'], sel, 'foreground'))
    if c is None:
        return None
    st = exact(s['rules'], sel, 'fontStyle') or ''
    rc = rgb(pool.role_value(s['rules'], role, None)) if role in pool.ROLES else None
    v = cr(c, s['bg'])
    # 同角色比亮度只在色相接近时算数: 色相不同说明原主题本就给了另一种颜色, 不是同色压暗
    same_hue = rc is not None and oklch(rc)[1] > NEUTRAL and oklch(c)[1] > NEUTRAL and \
        abs(math.degrees(math.atan2(math.sin(oklch(c)[2] - oklch(rc)[2]), math.cos(oklch(c)[2] - oklch(rc)[2])))) < DIM_HUE
    dim = v < s['med'] * DIM_ABS or (same_hue and v < cr(rc, s['bg']) * DIM_REL)
    return dict(neutral=oklch(c)[1] < NEUTRAL, dim=dim, bold='bold' in st, italic='italic' in st)


def generated():
    out = []
    for t in build():
        th = json.load(open(os.path.join(ROOT, 'themes', f"{t['name']}-color-theme.json")))
        bg = h(th['colors']['editor.background'][1:7])
        rules = {r['name'][8:]: r['settings'] for r in th['tokenColors'] if r.get('name', '').startswith('Comfort ')}
        # 调优后语法色对比度被压在 [下限, 正文] 窄区间里, 暗淡 = 贴近本主题彩色语法色的最低对比度
        low = min(cr(c, bg) for s in rules.values() if 'foreground' in s and oklch(c := h(s['foreground'][1:7]))[1] > NEUTRAL)
        look = {}
        for role, s in rules.items():
            c = h(s.get('foreground', th['colors']['editor.foreground'])[1:7])
            st = s.get('fontStyle', '')
            look[role] = dict(neutral=oklch(c)[1] < NEUTRAL, dim=cr(c, bg) <= low + 0.3, bold='bold' in st, italic='italic' in st)
        out.append((t['name'], look))
    return out


def tag(d):
    return ('灰' if d['neutral'] else '彩') + ('暗' if d['dim'] else '亮') + ('粗' if d['bold'] else '') + ('斜' if d['italic'] else '')


def main():
    P = pool.build(build())
    srcs, gens = sources(), generated()
    rows = []
    for sel, p in P.items():
        role = p['role']
        if role == pool.INHERIT or (not p['annotated'] and '--all' not in sys.argv):
            continue
        seen = [d for s in srcs if (d := src_look(s, sel, role))]
        if not seen:
            continue
        maj = lambda k: sum(d[k] for d in seen) * 2 > len(seen)
        src = {k: maj(k) for k in ('neutral', 'dim', 'bold', 'italic')}
        key = role + ' muted' if p.get('muted') else role
        g = [r[key] for _, r in gens if key in r]
        gen = dict(neutral=sum(d['neutral'] for d in g) * 2 > len(g), dim=sum(d['dim'] for d in g) * 2 > len(g),
                   bold=any(d['bold'] for d in g), italic=any(d['italic'] for d in g))
        nb = sum(d['bold'] for d in g)
        flags = []
        if src['dim'] and not gen['neutral'] and (gen['bold'] or not gen['dim']):
            flags.append('R1')
        if p['annotated'] and src['neutral'] and not gen['neutral'] and (gen['bold'] or not gen['dim']):
            flags.append('R2')
        if gen['bold'] and not src['bold']:
            flags.append('加粗')
        rows.append(dict(sel=sel, role=role, annotated=p['annotated'], tier=p['tier'], src=tag(src), n=len(seen),
                         gen=tag(gen) + (f'(粗{nb}/14)' if nb else ''), flags=flags))
    cnt = Counter((r['src'], r['gen'].split('(')[0]) for r in rows)
    print(f'共 {len(rows)} 条有原主题显式证据; 原观感 -> 生成观感(多数决):')
    for (a, b), n in sorted(cnt.items(), key=lambda x: -x[1]):
        print(f'  {a:5} -> {b:5} {n}')
    print('标记:', dict(Counter(f for r in rows for f in r['flags'])))
    for r in sorted(rows, key=lambda r: (not r['flags'], r['role'], r['sel'])):
        print(r['sel'], r['role'], '标注' if r['annotated'] else f"自动{r['tier']}", r['src'], f"{r['n']}源", r['gen'], ','.join(r['flags']), sep='\t')
    if '--json' in sys.argv:
        json.dump(rows, open(sys.argv[sys.argv.index('--json') + 1], 'w'), ensure_ascii=False, indent=1)


main()
