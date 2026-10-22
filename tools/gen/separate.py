# /// script
# requires-python = ">=3.11"
# ///
# 语法角色差异化: 按案例集的真实分词命中表(assets/layers/hits.json)核对 assets/layers/roles.json 里要分开的角色对, 并在调色链里把
# 撞色的角色对用主题自己的颜色拆开(步骤 syntax_separate). 判定口径与门禁线见 tools/gen/roles.py.
# 拆色: 撞色的(角色, 颜色)组整组换成主题自有颜色(原主题语法里的彩色 + 终端 6 色按语法下限调好的版本):
#   还原 先把层次更好的姊妹主题(同名深 / 浅, 原色下撞色更少)里本是另一种色相的组换回那个色相
#   拆开 再贪心挑代价最低的一步; 代价 = 撞色 + 偏好(偏离目标色相, 动已在目标色相上的组, 给灰色组上色, 占用别的主要角色的颜色);
#        代价不再下降时, 在能减少撞色的步里挑代价最低的继续
#   降到门禁线(前 5 名的中位数)即停, 只改到够用; 例外: 核心角色之间"必须分开"的对(MUST_CORE)达线后仍拆到不撞为止
#   目标色相: 层次更好的姊妹主题里同一批 token 的颜色, 否则主题自己的角色代表色
#   规则按选择器拆分, 换色的选择器紧跟原规则插入, 优先级不变.
# 命中表由 tools/textmate/layers-probe.mjs 对中间主题(assets/full-theme)分词得到: 调色步骤只改颜色不改规则结构, 所以命中关系在调色链里不变;
#   中间主题的规则结构变了(指纹不符)时报错, 先重跑 --update.
# 用法: uv run tools/gen/separate.py --update   重算命中表(需要本机 VS Code 的语法, 同 pool-guard), 随后重写 roles.json
#       uv run tools/gen/separate.py            按命中表报告各主题拆色前后的撞色与换色(不写文件)
#       uv run tools/gen/separate.py --check    同上, 有主题高于门禁线时退出码 1(不需要 VS Code)
#       uv run tools/gen/separate.py --real [主题目录]   用真实分词复测主题目录(默认 themes/), 高于门禁线时退出码 1(需要 VS Code)
import hashlib, json, math, os, re, subprocess, sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', d) for d in ('lib', 'gen', 'check')]
import pool
import roles as R
from colorlib import cr, fit, h, hx, oklch
from themefile import load, norm_hex

ROOT = R.ROOT
LAYERS = R.LAYERS
HITS = os.path.join(LAYERS, 'hits.json')
FULL = os.path.join(ROOT, 'assets', 'full-theme')
NEUTRAL_CHROMA = 0.035
# 换上的颜色与原色至少明显不同, 不靠刚越过阈值的近似色凑数
APART_DE = R.APART_DE
# 候选色去重: 与已收的候选 ΔE 小于它的算同一种颜色(比 R.SAME_DE 严, 只去掉几乎相同的)
CAND_DEDUP_DE = 3
# 候选色的最低彩度: 取 max(CAND_CHROMA, 主题语法彩色彩度中位数 x CAND_CHROMA_RATIO); 偏灰的颜色拆开了也不像主题的颜色
CAND_CHROMA, CAND_CHROMA_RATIO = 0.06, 0.7
# 贪心的偏好权重(与撞色同量纲: 一次撞色记 1): 色相离目标的距离, 动到已在目标色相上的组, 给灰色(正文色这类)的组上色, 动的 token 占比
W_HUE, W_HOME, W_GRAY, W_SIZE = 0.3, 5.0, 1.0, 0.05
# 主题的标志色多落在这几类角色上(如 One Dark 的红色标签, GitHub 的浅蓝字符串): 拆开阶段先只动其余角色, 降不到门禁线才放开, 且另加罚分
CORE, W_CORE = {'keyword', 'storage', 'function', 'string', 'type', 'tag', 'heading'}, 3.0
# 两个角色都在 CORE 且参照家族里分开的占比达到"必须分开"(roles.json 的 auto)的对: 主要角色撞色最显眼(如 Night Owl 的字符串与类型),
# 不受门禁线限制; 达线后再拆, 每步须减少这类撞色, 且总撞色不超过 max(当前撞色, 门禁线): 已达线时不越过门禁线, 未达线时不增加
MUST_CORE = '必须分开'
# 换上的颜色已被另一个主要(token 占比 >= OCCUPIED_SHARE)的异角色组占用时的罚分
W_OCC, OCCUPIED_SHARE = 0.5, 0.02
# 还原阶段: 姊妹主题里该组色相与现色相差 >= RESTORE_GAP(度)时, 换到与目标色相差 <= RESTORE_NEAR 的候选色
RESTORE_GAP, RESTORE_NEAR = 30, 45
# 只限制"拆开"阶段的贪心步数(不含还原阶段与 MUST_CORE 的达线后拆分)
MAX_MOVES = 16


def corpus_files() -> list[str]:
    return [os.path.join(ROOT, f) for f in R.case_files()]


def _hex(v) -> str | None:
    n = norm_hex(v)
    return n[:7] if n else None


def selectors(rules: list) -> list[tuple[int, str]]:
    """有前景色的规则按选择器展开, 保持原顺序: [(规则下标, 选择器)]."""
    return [(i, s) for i, r in enumerate(rules) if r.get('scope') and _hex((r.get('settings') or {}).get('foreground')) for s in pool.scopes_of(r)]


def fingerprint(rules: list) -> str:
    return hashlib.sha1(json.dumps(selectors(rules)).encode()).hexdigest()[:16]


_std = None


def standard() -> dict:
    global _std
    if _std is None:
        _std = json.load(open(R.OUT, encoding='utf-8'))
    return _std


def checks_of(tokens: list) -> list[tuple]:
    std = standard()
    return R.checks(tokens, R.separate_set(std), set(std['exempt']))


_hits = None


def hits() -> dict:
    global _hits
    if _hits is None:
        _hits = json.load(open(HITS, encoding='utf-8'))
    return _hits


_rule_roles = None


def rule_roles() -> dict:
    global _rule_roles
    if _rule_roles is None:
        _rule_roles = json.load(open(os.path.join(ROOT, 'assets', 'pool', 'full-rule.json'), encoding='utf-8'))['rules']
    return _rule_roles


def _sel_role(sel: str, roles_of: dict) -> str | None:
    r = roles_of.get(sel) or pool.struct_role(sel)
    return None if r in (None, pool.INHERIT) else r


def _hue_gap(a: str, b: str) -> float:
    """两色的色相差(度, 0~180); 任一方是灰色时色相无意义, 记 180(当作不同)."""
    (_, ca, ha), (_, cb, hb) = oklch(h(a)), oklch(h(b))
    if ca <= NEUTRAL_CHROMA or cb <= NEUTRAL_CHROMA:
        return 180.0
    d = abs(math.degrees(ha - hb)) % 360
    return min(d, 360 - d)


REPORT: dict[str, dict] = {}


class State:
    """当前覆盖色下每条核对的撞色概率; 换一组的颜色时只重算这组 token 涉及的核对."""

    def __init__(self, base: list[str], checks: list[tuple]):
        self.base, self.checks = base, checks
        self.of_token = defaultdict(list)
        for i, (_, _, ta, tb) in enumerate(checks):
            for k in ta + tb:
                self.of_token[k].append(i)
        self.over: dict[int, str] = {}
        self.ws = [R.weight(base, ta, tb) for _, _, ta, tb in checks]

    def colors(self, over: dict[int, str]) -> list[str]:
        out = list(self.base)
        for k, c in over.items():
            out[k] = c
        return out

    def score(self, ws: list[float]) -> dict:
        return dict(n=sum(w >= R.COLLIDE for w in ws), w=sum(ws))

    def trial(self, tokens: list[int], c: str):
        over = dict(self.over)
        over.update({k: c for k in tokens})
        colors = self.colors(over)
        ws = list(self.ws)
        for i in {i for k in tokens for i in self.of_token.get(k, ())}:
            _, _, ta, tb = self.checks[i]
            ws[i] = R.weight(colors, ta, tb)
        return over, ws

    def bad_roles(self) -> set[str]:
        return {r for (_, k, _, _), w in zip(self.checks, self.ws) if w >= R.COLLIDE for r in k.split('|')}


def fix(rules: list, src: dict, t: dict, comment_rule) -> list:
    """rules: 与 src['tokenColors'] 下标一一对应的已调色规则; 返回拆色后的规则(只增选择器级的新规则, 不删原规则)."""
    name = t['name']
    H = hits()
    entry = H['themes'].get(name)
    if entry is None or entry['fingerprint'] != fingerprint(src.get('tokenColors', [])):
        raise SystemExit(f'{name}: 语法层次命中表与中间主题不符, 先运行 uv run tools/gen/separate.py --update')
    # 命中表的 token 下标按案例集的顺序记; 案例集增删或调序后旧表会错位
    if H['files'] != [os.path.relpath(f, ROOT) for f in corpus_files()]:
        raise SystemExit(f'{name}: 语法层次命中表与案例集(assets/layers/cases.json)不符, 先运行 uv run tools/gen/separate.py --update')
    gate = standard()['rules']['gate']
    tokens = H['tokens']
    checks = checks_of(tokens)
    sels = [tuple(x) for x in entry['selectors']]
    hit = entry['hits']
    fg, bg = hx(t['fg']), t['bg']
    color = {x: _hex(rules[x[0]]['settings'].get('foreground')) or fg for x in sels}
    sel_index = {x: i for i, x in enumerate(sels)}
    st = State([fg if k < 0 else color[sels[k]] for k in hit], checks)
    before = st.score(st.ws)
    # 组: (角色, 颜色簇); 命中的选择器按它上色的 token 多数角色归组, 没命中的按规则池角色归组
    votes = defaultdict(Counter)
    for k, si in enumerate(hit):
        if si >= 0 and (c := R.canon(tokens[k][2])) is not None:
            votes[sels[si]][c] += 1
    roles_of = rule_roles()
    comments = {x for x in sels if comment_rule(rules[x[0]])}
    comment_colors = {color[x] for x in comments}
    groups = []
    for x in sels:
        if x in comments:
            continue
        r = votes[x].most_common(1)[0][0] if votes[x] else R.canon(_sel_role(x[1], roles_of) or '')
        if r is None or r == 'comment':
            continue
        for g in groups:
            if g['role'] == r and R.de(g['color'], color[x]) < R.SAME_DE:
                g['sels'].append(x)
                break
        else:
            groups.append(dict(role=r, color=color[x], sels=[x]))
    for g in groups:
        idx = {sel_index[x] for x in g['sels']}
        g['tokens'] = [k for k, si in enumerate(hit) if si in idx]
    groups = [g for g in groups if g['tokens']]
    # 候选色: 主题自己的语法彩色(错误 / 删除 / 新增这类标记色除外) + 终端 6 色(界面色源, 已按语法下限调好); 太近正文 / 注释的不要, 近似色去重
    cands = []
    chromas = sorted(oklch(h(color[x]))[1] for x in sels if x not in comments and oklch(h(color[x]))[1] > NEUTRAL_CHROMA)
    min_chroma = max(CAND_CHROMA, CAND_CHROMA_RATIO * chromas[len(chromas) // 2]) if chromas else CAND_CHROMA
    marks = {'invalid', 'deleted', 'inserted'}
    raw = [color[x] for x in sels if x not in comments and _sel_role(x[1], roles_of) not in marks]
    raw += [hx(t.get('ui_ansi', t['ansi'])[n]) for n in ('Red', 'Green', 'Yellow', 'Blue', 'Magenta', 'Cyan')]
    for c in dict.fromkeys(raw):
        rgb = h(c)
        if oklch(rgb)[1] < min_chroma:
            continue
        if cr(rgb, bg) < t['token_min']:
            c = hx(fit(rgb, bg, lo=t['token_min'] + 0.02))
        if R.de(c, fg) < R.SAME_DE or any(R.de(c, x) < R.SAME_DE for x in comment_colors) or any(R.de(c, x) < CAND_DEDUP_DE for x in cands):
            continue
        cands.append(c)
    # 目标色相: 同一批 token 在原色下撞色更少的姊妹主题(同名深 / 浅)里的颜色(多数票); 否则取主题自己的角色代表色; 灰色不作目标
    twin = name.replace('-dark', '-@').replace('-light', '-dark').replace('-@', '-light')
    twin_path = os.path.join(FULL, f'{twin}-full.json')

    def source_colors(rules_: list, entry_: dict, fg_: str) -> list[str]:
        return [fg_ if k < 0 else _hex(rules_[entry_['selectors'][k][0]]['settings']['foreground']) for k in entry_['hits']]

    src_fg = _hex(src.get('colors', {}).get('editor.foreground')) or fg
    better = False
    if twin in H['themes'] and os.path.exists(twin_path):
        tw = load(twin_path)
        tw_color = source_colors(tw.get('tokenColors', []), H['themes'][twin], _hex(tw['colors'].get('editor.foreground')) or '#808080')
        own = source_colors(src.get('tokenColors', []), entry, src_fg)
        # 只向层次更好的姊妹主题看齐: 两边互相当参照会把好的一边也拉坏(如 Night Owl 的桃色字符串)
        better = R.judge(tw_color, checks)['w'] < R.judge(own, checks)['w']
    target, from_twin = {}, set()
    for g in groups:
        v = None
        if better:
            tv = Counter(tw_color[k] for k in g['tokens'])
            v = tv.most_common(1)[0][0] if tv else None
        if v and oklch(h(v))[1] >= CAND_CHROMA:
            from_twin.add(id(g))
        elif g['role'] in pool.ROLES:
            v = _hex(pool.role_value(src.get('tokenColors', []), g['role'], src_fg))
        if v and oklch(h(v))[1] >= CAND_CHROMA:
            target[id(g)] = v
    n_tok = len(hit) or 1
    now = {id(g): g['color'] for g in groups}

    def occupied(g, c) -> bool:
        return any(o is not g and o['role'] != g['role'] and len(o['tokens']) >= OCCUPIED_SHARE * n_tok and R.de(now[id(o)], c) < R.SAME_DE
                   for o in groups)

    def penalty(g, c) -> float:
        tv = target.get(id(g))
        p = W_HUE * (_hue_gap(c, tv) / 180 if tv else 0.5) + W_SIZE * len(g['tokens']) / n_tok
        if tv and _hue_gap(g['color'], tv) < RESTORE_GAP:
            p += W_HOME
        if oklch(h(g['color']))[1] <= NEUTRAL_CHROMA:
            p += W_GRAY
        if g['role'] in CORE:
            p += W_CORE
        return p + (W_OCC if occupied(g, c) else 0)

    def cost(m: dict, pen: float) -> float:
        return m['n'] + m['w'] + pen

    moves, pen, cur, chosen = [], 0.0, before, {}

    def apply(g, c, over, ws, kind):
        nonlocal cur
        st.over, st.ws = over, ws
        cur = st.score(ws)
        g['moved'] = True
        now[id(g)] = c
        chosen.update({x: c for x in g['sels']})
        moves.append(dict(role=g['role'], old=g['color'], new=c, selectors=len(g['sels']), tokens=len(g['tokens']), target=target.get(id(g)), kind=kind))

    # 还原: 处在撞色里, 而层次更好的姊妹主题里这批 token 是另一种色相的组, 先换到姊妹主题的色相(主题自有色里最接近的), 撞色下降才接受;
    # 候选离目标色相最近的组先挑, 免得别的组先占走它最合适的颜色
    def fit_gap(g) -> float:
        tv = target.get(id(g))
        return min((_hue_gap(c, tv) for c in cands if tv and R.de(c, g['color']) >= APART_DE), default=180.0)

    for g in sorted(groups, key=lambda g: (fit_gap(g), -len(g['tokens']))):
        tv = target.get(id(g))
        if cur['n'] <= gate:
            break
        if id(g) not in from_twin or oklch(h(g['color']))[1] <= NEUTRAL_CHROMA or _hue_gap(g['color'], tv) < RESTORE_GAP:
            continue
        if g['role'] not in st.bad_roles():
            continue
        best = None
        for c in cands:
            if R.de(c, g['color']) >= APART_DE and _hue_gap(c, tv) <= RESTORE_NEAR and not occupied(g, c):
                over, ws = st.trial(g['tokens'], c)
                m = st.score(ws)
                v = (m['w'], _hue_gap(c, tv))
                if best is None or v < best[0]:
                    best = (v, c, m, over, ws)
        if best and best[2]['w'] < cur['w'] - 1e-9 and best[2]['n'] <= cur['n']:
            apply(g, best[1], best[3], best[4], '还原')

    restored = len(moves)
    # 先只动非核心角色; 降不到门禁线时才放开核心角色
    allow_core = False
    while len(moves) - restored < MAX_MOVES and cur['n'] > gate:
        options = []
        for g in groups:
            if g.get('moved') or (g['role'] in CORE and not allow_core):
                continue
            for c in cands:
                if R.de(c, g['color']) >= APART_DE:
                    over, ws = st.trial(g['tokens'], c)
                    options.append((g, c, st.score(ws), penalty(g, c), over, ws))
        best = min(options, key=lambda x: cost(x[2], pen + x[3]), default=None)
        if best is not None and cost(best[2], pen + best[3]) >= cost(cur, pen) - 1e-6:
            # 偏好让代价不再下降但仍高于门禁线: 在能减少撞色的步里挑代价最低的
            fewer = [x for x in options if (x[2]['n'], x[2]['w']) < (cur['n'], cur['w'] - 1e-9)]
            best = min(fewer, key=lambda x: cost(x[2], pen + x[3]), default=None)
        if best is None:
            if allow_core:
                break
            allow_core = True
            continue
        g, c, m, p, over, ws = best
        pen += p
        apply(g, c, over, ws, '拆开')
    must_core = {k for k, p in standard()['pairs'].items() if p['auto'] == MUST_CORE and set(k.split('|')) <= CORE}

    def core_bad(ws: list[float]) -> list[str]:
        return [k for (_, k, _, _), w in zip(checks, ws) if w >= R.COLLIDE and k in must_core]

    # 每对只动全主题 token 少的那个角色: 两边都是主要角色, 换大的一方等于换掉主题的标志色(如 GitHub 的浅蓝字符串); 拆不开就保持原样
    role_size = Counter()
    for g in groups:
        role_size[g['role']] += len(g['tokens'])
    while bad_core := core_bad(st.ws):
        roles_bad = {min(k.split('|'), key=lambda r: role_size[r]) for k in bad_core}
        options = []
        for g in groups:
            if g.get('moved') or g['role'] not in roles_bad:
                continue
            for c in cands:
                if R.de(c, g['color']) >= APART_DE:
                    over, ws = st.trial(g['tokens'], c)
                    m = st.score(ws)
                    if len(core_bad(ws)) < len(bad_core) and m['n'] <= max(cur['n'], gate):
                        options.append((g, c, m, penalty(g, c), over, ws))
        best = min(options, key=lambda x: cost(x[2], pen + x[3]), default=None)
        if best is None:
            break
        g, c, m, p, over, ws = best
        pen += p
        apply(g, c, over, ws, '拆开')
    bad = [(f, k) for (f, k, _, _), w in zip(checks, st.ws) if w >= R.COLLIDE]
    REPORT[name] = dict(before=before, after=dict(cur, bad=bad), moves=moves, gate=gate)
    if not chosen:
        return rules
    out = []
    for ri, r in enumerate(rules):
        moved = {s: chosen[(ri, s)] for s in pool.scopes_of(r) if (ri, s) in chosen} if r.get('scope') else {}
        if not moved:
            out.append(r)
            continue
        rest = [s for s in pool.scopes_of(r) if s not in moved]
        if rest:
            out.append(dict(r, scope=rest))
        for c in dict.fromkeys(moved.values()):
            out.append(dict(r, scope=[s for s, v in moved.items() if v == c], settings=dict(r['settings'], foreground=c)))
    return out


def update() -> int:
    from themes import build
    themes = {t['name']: load(os.path.join(FULL, t['full'])).get('tokenColors', []) for t in build()}
    files = corpus_files()
    inp = dict(files=files, themes={n: [s for _, s in selectors(r)] for n, r in themes.items()})
    p = subprocess.run(['node', os.path.join(ROOT, 'tools', 'textmate', 'layers-probe.mjs')], input=json.dumps(inp), capture_output=True,
                       text=True, cwd=ROOT, timeout=600)
    if p.returncode:
        print(p.stderr.strip()[-2000:])
        return 1
    res = json.loads(p.stdout)
    out = dict(files=[os.path.relpath(f, ROOT) for f in files], tokens=[[f, ln, R.role(sc)] for f, ln, sc in res['tokens']],
               themes={n: dict(fingerprint=fingerprint(r), selectors=selectors(r), hits=res['themes'][n]) for n, r in themes.items()})
    text = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    # 每个主题一行, 便于看 diff
    text = re.sub(r'(?<=[{,])("[a-z]+-(?:dark|light)":)', r'\n\1', text)
    open(HITS, 'w', encoding='utf-8').write(text + '\n')
    print(f'hits.json: {len(files)} 个案例, {len(out["tokens"])} 个 token, {len(themes)} 套主题')
    R.write()
    return 0


def describe(bad: list, files: list[str]) -> str:
    return ', '.join(f"{k}@{os.path.basename(files[f])}" for f, k in bad[:5]) + (' …' if len(bad) > 5 else '')


def real(theme_dir: str) -> int:
    """用真实分词复测主题目录, 口径与命中表模型相同."""
    gate, files, bad = standard()['rules']['gate'], R.case_files(), 0
    for name, (tokens, colors) in sorted(R.tokenize(theme_dir).items()):
        m = R.judge(colors, checks_of(tokens))
        bad += m['n'] > gate
        print(f"{name:14} 撞色 {m['n']:3}  {'达线' if m['n'] <= gate else '高于门禁线'}  {describe(m['bad'], files)}")
    return 1 if bad else 0


def main() -> int:
    if '--update' in sys.argv:
        return update()
    if '--real' in sys.argv:
        rest = sys.argv[sys.argv.index('--real') + 1:]
        return real(os.path.abspath(rest[0]) if rest else os.path.join(ROOT, 'themes'))
    # gen_vscode 导入的是模块 separate, 不是这里的 __main__, 报告要从那份模块里取
    import separate as mod
    from gen_vscode import render
    from themes import build
    for t in build():
        render(t)
    files = hits()['files']
    bad = 0
    for name, r in mod.REPORT.items():
        b, a, gate = r['before'], r['after'], r['gate']
        bad += a['n'] > gate
        print(f"{name:14} 撞色 {b['n']:3} -> {a['n']:3}(门禁线 {gate})  {'达线' if a['n'] <= gate else '高于门禁线'}  {describe(a['bad'], files)}")
        for m in r['moves']:
            print(f"    {m['kind']} {m['role']:12} {m['old']} -> {m['new']}  ({m['selectors']} 个选择器, {m['tokens']} 个 token, 目标 {m['target'] or '-'})")
    if '--check' in sys.argv and not mod.REPORT:
        print('syntax_separate 步骤关闭, 没有可核对的拆色结果')
        return 1
    return 1 if '--check' in sys.argv and bad else 0


if __name__ == '__main__':
    sys.exit(main())
