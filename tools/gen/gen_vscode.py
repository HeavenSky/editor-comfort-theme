# /// script
# requires-python = ">=3.11"
# ///
# 调色链: 补全段的中间主题 assets/full-theme/<name>-full.json(complete.py)经 tools/gen/steps.py 登记的调色步骤生成 VS Code 颜色主题 themes/<name>.json.
# 一切改色都必须是登记过的步骤: COMFORT_STEPS=none 时产物与 full 逐键相等(--identity 校验).
# 用法: uv run tools/gen/gen_vscode.py [--check] [--out <目录>]   (--check: 只比对, 产物与生成结果不一致时退出码 1;
#       --out: 写到别的目录, 不动 themes/, 供 compare-steps.mjs 按不同 COMFORT_STEPS 生成对比用)
#       COMFORT_STEPS=none uv run tools/gen/gen_vscode.py --identity   全关产物与 full 的 colors / tokenColors / semanticTokenColors 不等时退出码 1
# themes/*.json 是生成物: 手改会在下次生成时被覆盖, 要改颜色改 themes.py 或 assets/source/ 的输入.
import json, math, os, re, sys

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', d) for d in ('lib', 'gen', 'check', 'lab')]
from colorlib import WHITE_C, WHITE_L, Rgb, unwhite, blend, cr, de2000, fit, from_oklch, h, hx, lum, oklch, sat, with_sat
import levels, separate
from schema import FONT_STYLE, HEX, RULE_KEYS, SEMANTIC_STYLE_KEYS, SETTINGS_KEYS, TRANSPARENT, problems
from comfort import HIGHLIGHT_KEYS, HIGHLIGHT_TEXT_MIN, INPUT_SELECTION_TEXT, SELECTION_VISIBLE, STATUS_GROUPS, input_selection
from themes import ANSI, LEGIBLE, TERM_MARGIN, build
from steps import on

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'source')
# 补全段的中间主题 <name>-full.json(complete.py 生成, 不进版本库)
FULL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'full-theme')
REGISTRY = os.path.join(SOURCES, '..', 'vscode', 'color-registry.json')
OUT = os.path.join(ROOT, 'themes')

# 界面上的文字与其底色, 及对比度下限(非活动的图标 / 标签本就该淡一档, 下限 3.0); metrics.py 用同一张表评级
UI_PAIRS = [
    ('editorLineNumber.foreground', 'editor.background', 2.2),
    ('sideBar.foreground', 'sideBar.background', 4.5),
    ('tab.activeForeground', 'tab.activeBackground', 4.5),
    ('tab.inactiveForeground', 'tab.inactiveBackground', 3.0),
    ('statusBar.foreground', 'statusBar.background', 4.5),
    ('activityBar.foreground', 'activityBar.background', 4.5),
    ('activityBar.inactiveForeground', 'activityBar.background', 3.0),
    ('sideBarTitle.foreground', 'sideBar.background', 4.5),
    ('sideBarSectionHeader.foreground', 'sideBarSectionHeader.background', 4.5),
    ('titleBar.activeForeground', 'titleBar.activeBackground', 4.5),
    # 没有定义 sideBar.foreground 的主题(如 Ayu)文件树用通用前景色
    ('foreground', 'sideBar.background', 4.5),
]
# 画在代码上的界面色, 按语法色的规则调色
TEXT_ON_CODE = ('editorBracketHighlight.foreground',)
# 原主题不定义括号色时, 用原主题的 数字 / 关键字 / 转义 色补上, 而不是落到注册表的通用补色
BRACKET_FALLBACK = ['constant.numeric', 'keyword.control', 'constant.character.escape']
NEUTRAL_CHROMA = 0.035
SAME_COLOR = 0.012
COMMENT_RATIO = 1.85
COMMENT_RANGE = (3.4, 4.2)


def is_area(key: str) -> bool:
    """画成一片的颜色(底色, 边框, 阴影): 仍按 cap(彩度)与对比度安静处理; 其余(文字, 图标)按饱和度平滑压缩."""
    return key.lower().endswith(('background', 'border', 'shadow'))


def load(path: str) -> dict:
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    return json.loads(s)


def parse(v) -> tuple[Rgb, str] | None:
    if not isinstance(v, str):
        return None
    v = {'white': '#FFFFFF', 'black': '#000000'}.get(v.lower(), v)
    m = re.fullmatch(r'#([0-9A-Fa-f]{3,8})', v)
    if not m:
        return None
    s = m.group(1)
    if len(s) in (3, 4):
        s = ''.join(c * 2 for c in s)
    return h(s[:6]), s[6:8].upper()


def dist(a: Rgb, b: Rgb) -> float:
    (L1, C1, H1), (L2, C2, H2) = oklch(a), oklch(b)
    return math.dist((L1, C1 * math.cos(H1), C1 * math.sin(H1)), (L2, C2 * math.cos(H2), C2 * math.sin(H2)))


def scopes_of(rule: dict) -> list[str]:
    sc = rule.get('scope') or []
    return [x.strip() for x in (sc.split(',') if isinstance(sc, str) else sc)]


def resolve(rules: list, scope: str) -> str | None:
    # 选择器是 scope 的点分前缀即命中, 最长者胜; 只用于补括号色, 不处理后代选择器
    best, color = -1, None
    for r in rules:
        fg = r.get('settings', {}).get('foreground')
        for sel in scopes_of(r):
            if fg and ' ' not in sel and (scope == sel or scope.startswith(sel + '.')) and len(sel) > best:
                best, color = len(sel), fg
    return color


def source_fg(src: dict, dark: bool) -> str:
    # 原主题的正文色: editor.foreground, foreground, 无 scope 的全局规则, 都没有时就是 VS Code 的默认正文色
    c = src['colors']
    glob = [r['settings']['foreground'] for r in src.get('tokenColors', []) if not r.get('scope') and r.get('settings', {}).get('foreground')]
    reg = json.load(open(REGISTRY, encoding='utf-8'))['colors']['editor.foreground']
    return c.get('editor.foreground') or c.get('foreground') or (glob[0] if glob else reg['dark' if dark else 'light'])


def hardcoded_keys(dark: bool) -> dict[str, str]:
    """VS Code 注册表中默认值是硬编码字面量的键 -> 该默认值; 主题不定义这些键时界面会落到与主题无关的颜色."""
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    mode = 'dark' if dark else 'light'
    return {k: v[mode] for k, v in reg['colors'].items() if v.get(mode) and not v.get('deprecated')}


# 已废弃颜色键的官方替代键(VS Code deprecationMessage 所指); 其余废弃键与未注册的键直接丢弃
DEPRECATED_RENAME = {
    'editorActiveLineNumber.foreground': 'editorLineNumber.activeForeground',
    'editorIndentGuide.background': 'editorIndentGuide.background1',
    'editorIndentGuide.activeBackground': 'editorIndentGuide.activeBackground1',
}


def translucent(target: Rgb, bg: Rgb) -> str:
    # 须半透明的颜色: 取叠到编辑区底上后与 target 相同的最小透明度, 观感不变而不再遮住下面的内容
    for i in range(25, 96):
        a = i / 100
        c = [(x - (1 - a) * y) / a for x, y in zip(target, bg)]
        if all(-1e-6 <= v <= 1 + 1e-6 for v in c):
            return hx(tuple(min(1, max(0, v)) for v in c)) + '%02X' % round(a * 255)
    return hx(target) + 'F2'


def conform(colors: dict, rules: list, semantic: dict, t: dict) -> None:
    """按 vscode://schemas/color-theme 清理: VS Code 会忽略或报错的写法改成等效的合法写法, 改不了的丢弃."""
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    known = reg['colors']
    for old, new in DEPRECATED_RENAME.items():
        if old in colors:
            colors.setdefault(new, colors[old])
    for k in list(colors):
        info = known.get(k)
        if info is None or info.get('deprecated') or not (isinstance(colors[k], str) and HEX.match(colors[k])):
            del colors[k]
        elif info.get('transparent') and not TRANSPARENT.match(colors[k]):
            colors[k] = translucent(opaque(colors, k, t['bg']), t['bg'])
    kept = []
    for r in rules:
        st = r.get('settings')
        if not isinstance(st, dict):
            continue
        for k in [k for k in r if k not in RULE_KEYS]:
            del r[k]
        # token 背景色已废弃且不生效; 其余不在 schema 里的字段(CSS 属性等)同样不生效
        for k in [k for k in st if k not in SETTINGS_KEYS or k == 'background']:
            del st[k]
        if 'fontStyle' in st and not FONT_STYLE.match(str(st['fontStyle'])):
            # TextMate 的 normal / regular 意为取消样式, schema 里的等效写法是空字符串
            st['fontStyle'] = '' if str(st['fontStyle']).strip().lower() in ('normal', 'regular', 'none') else None
            if st['fontStyle'] is None:
                del st['fontStyle']
        if st:
            kept.append(r)
    rules[:] = kept
    selector = re.compile(reg['semanticSelector'])
    for k in list(semantic):
        v = semantic[k]
        if not selector.match(k):
            del semantic[k]
        elif isinstance(v, dict):
            for f in [f for f in v if f not in SEMANTIC_STYLE_KEYS or f == 'background']:
                del v[f]
            if not v:
                del semantic[k]


class Mapper:
    """把原主题的颜色映射到目标主题: 语法色低于下限的提到下限, 注释低于下限的提上来; 底色变了时界面中性色随底色平移明度;
    VS Code 默认的彩色取本主题同色相的终端色."""

    def __init__(self, t: dict, src: dict):
        self.t = t
        c = src['colors']
        self.src_bg = parse(c['editor.background'])[0]
        self.src_fg = parse(source_fg(src, t['dark']))[0]
        self.dl = oklch(t['bg'])[0] - oklch(self.src_bg)[0]
        normal = [t.get('ui_ansi', t['ansi'])[n] for n in ANSI[1:7]]
        self.hues = [(oklch(c)[2], c) for c in normal]
        # 注释对比度: 'auto' 随正文联动, 正文 / COMMENT_RATIO, 限制在 COMMENT_RANGE 内
        target = t.get('comment_cr')
        if target == 'auto':
            target = min(COMMENT_RANGE[1], max(COMMENT_RANGE[0], cr(t['fg'], t['bg']) / COMMENT_RATIO))
        self.comment_cr = target
        self.text = cr(t['fg'], t['bg'])
        # 底色 / 正文没变时不做吸附与平移, 未调整的颜色原样输出(全关时与补全段产物逐键相等)
        self.bg_same, self.fg_same = hx(t['bg']) == hx(self.src_bg), hx(t['fg']) == hx(self.src_fg)

    def target_cr(self, c: float) -> float:
        """语法色的目标对比度: syntax_floor 开时低于 token_min 的抬到 token_min, 本来够读的不动."""
        return max(self.t['token_min'], c) if on('syntax_floor') else c

    def token(self, v, comment: bool = False) -> str | None:
        # 全透明(如括号色 4~6 的 #00000000)表示不着色, VS Code 跳过它只循环前 3 色; 按语法色抬到可读会变成不透明的灰括号
        if (q := parse(v)) and q[1] == '00':
            return v
        out, p = self._token(v, comment), parse(v)
        # 半透明色没被调整(叠到底上的实际颜色不变)时保留原写法, 不改成不透明
        if out is None or p is None or not p[1] or not self.bg_same:
            return out
        q = parse(out)
        return hx(p[0]) + p[1] if q and not q[1] and hx(q[0]) == hx(blend(p[0], self.src_bg, int(p[1], 16) / 255)) else out

    def _token(self, v, comment: bool = False) -> str | None:
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        near_fg = dist(rgb, self.src_fg) < SAME_COLOR and not self.fg_same
        if near_fg and not alpha:
            return hx(self.t['fg'])
        src_c = rgb
        if alpha:
            # 半透明语法色(原主题用来弱化标点)按叠到底色上的实际颜色调对比度, 输出不透明色
            a = int(alpha, 16) / 255
            base = self.t['fg'] if near_fg else rgb
            src_c = blend(self.src_fg if base is self.t['fg'] else rgb, self.src_bg, a)
            rgb, alpha = blend(base, self.t['bg'], a), ''
        bg = self.t['bg']
        L, C, H = oklch(rgb)
        if comment:
            if self.comment_cr is None:
                return hx(rgb) + alpha
            if on('comment_floor') and cr(rgb, bg) < COMMENT_RANGE[0]:
                return hx(fit(rgb, bg, lo=COMMENT_RANGE[0] + 0.02)) + alpha
            return hx(rgb) + alpha
        # 对比度已在目标上时原样保留, 不经 OKLCH 往返; 否则只调明度, 色相与饱和度不变
        target = self.target_cr(cr(src_c, self.src_bg))
        if abs(cr(rgb, bg) - target) <= 0.01:
            return hx(rgb) + alpha
        s = sat(rgb)
        return hx(fit(with_sat(L, s, H), bg, lo=target, hi=target, s=s)) + alpha

    def ui(self, v, ref_bg: Rgb | None = None) -> str | None:
        # ref_bg: 该颜色所在体系的编辑区底; 原主题的颜色用原主题底, VS Code 默认色用 VS Code 默认主题的底
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        own = ref_bg is None
        ref_bg = ref_bg or self.src_bg
        if dist(rgb, ref_bg) < SAME_COLOR and not (own and self.bg_same):
            return hx(self.t['bg']) + alpha
        if own and dist(rgb, self.src_fg) < SAME_COLOR and not self.fg_same:
            return hx(self.t['fg']) + alpha
        L, C, H = oklch(rgb)
        if C < NEUTRAL_CHROMA and not (own and self.bg_same):
            # 中性色随底色平移明度
            return hx(from_oklch(L + oklch(self.t['bg'])[0] - oklch(ref_bg)[0], C, H)) + alpha
        return hx(rgb) + alpha

    def accent(self, v) -> str | None:
        # VS Code 默认的彩色映射到本主题同色相的终端色, 保留原透明度
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        L, C, H = oklch(rgb)
        if C < NEUTRAL_CHROMA:
            return None
        near = min(self.hues, key=lambda x: abs(math.atan2(math.sin(x[0] - H), math.cos(x[0] - H))))
        return hx(near[1]) + alpha

    def tint(self, v, ref_bg: Rgb) -> str | None:
        # 背景类默认色: 色相取本主题同色相的终端色, 明度保留默认值(随底色平移), 彩度不变; 不把暗底色换成亮色块
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        L, C, H = oklch(rgb)
        if C < NEUTRAL_CHROMA:
            return None
        near = min(self.hues, key=lambda x: abs(math.atan2(math.sin(x[0] - H), math.cos(x[0] - H))))
        L += oklch(self.t['bg'])[0] - oklch(ref_bg)[0]
        return hx(from_oklch(L, C, oklch(near[1])[2])) + alpha


def opaque(colors: dict, key: str, under: Rgb) -> Rgb | None:
    p = parse(colors.get(key))
    if p is None:
        return None
    rgb, alpha = p
    return blend(rgb, under, int(alpha, 16) / 255) if alpha else rgb


def fill_hardcoded(colors: dict, t: dict, m: Mapper) -> None:
    # 注册表里默认值硬编码的键, 主题没定义的一律按本主题色板补齐, 不让任何界面落到与主题无关的颜色
    hard = hardcoded_keys(t['dark'])
    vs_bg = parse(hard['editor.background'])[0]
    for k, default in hard.items():
        if k in colors:
            continue
        # 默认值全透明的(如括号色 4~6 的 #00000000, 表示不着色)原样保留; 混到底色上会变成与底同色的不透明色, 字就看不见了
        p = parse(default)
        if p and p[1] == '00':
            colors[k] = default
            continue
        if k.startswith(TEXT_ON_CODE):
            out = m.token(default)
        elif k.lower().endswith('background'):
            out = m.tint(default, vs_bg)
        else:
            out = m.accent(default)
            out = out and (out if is_area(k) else default_cr(out, default, t['bg'], vs_bg))
        colors[k] = out or m.ui(default, vs_bg)


# 补出的界面文字色对底色的对比度要求上限: 与看不清类步骤的正文 / 语法 / 终端可读下限一致
FILL_TEXT_CR = 4.5


def default_cr(v: str, default: str, bg: Rgb, vs_bg: Rgb) -> str:
    """补出的界面文字 / 图标色(色相取终端色)对本主题底色的对比度不低于 VS Code 默认色对默认底色的对比度, 但最多要求到 FILL_TEXT_CR:
    明度往远离底色的方向调, 色相与饱和度不变, 保留透明度. 浅色主题的终端黄(如 Owl Light #E0AF02)直接拿来当 git 修改标记会比默认棕色浅;
    VS Code 深色默认色对比度多在 9~10, 不封顶会把深色主题本来够读的终端色都提成浅色, 偏离原主题."""
    (rgb, alpha), (drgb, dalpha) = parse(v), parse(default)
    a = int(alpha, 16) / 255 if alpha else 1.0
    goal = min(FILL_TEXT_CR, cr(blend(drgb, vs_bg, int(dalpha, 16) / 255) if dalpha else drgb, vs_bg))
    L, _, H = oklch(rgb)
    s, step, out = sat(rgb), (0.004 if lum(rgb) >= lum(bg) else -0.004), rgb
    while cr(blend(out, bg, a), bg) < goal and 0 < L + step < 1:
        L += step
        out = with_sat(L, s, H)
    return hx(out) + alpha


# 状态色组内两两色差目标(门禁清晰理想 15): 原主题没定义而由 fill_hardcoded 补出的状态色, 撞上同组颜色时改取另一个终端色
STATUS_DE = 15.0


def status_apart(colors: dict, src_colors: dict, t: dict, m: 'Mapper') -> None:
    from colorlib import de2000
    bg = t['bg']
    for group in STATUS_GROUPS:
        for k in group:
            if k in src_colors or k not in colors:
                continue
            others = [opaque(colors, o, bg) for o in group if o != k and o in colors]
            cur = opaque(colors, k, bg)
            if not others or min(de2000(cur, o) for o in others) >= STATUS_DE:
                continue
            hard = hardcoded_keys(t['dark'])
            vs_bg = parse(hard['editor.background'])[0]
            cands = [default_cr(v, hard[k], bg, vs_bg) if k in hard and not is_area(k) else v for _, c in m.hues if (v := m.accent(hx(c)))]
            colors[k] = max(cands, key=lambda v: min(de2000(parse(v)[0], o) for o in others))


def selections(colors: dict, t: dict) -> None:
    """编辑区选区与输入框里选中文字的底(搜索框, 筛选框等): 与各自底色的对比度到 选区可见 理想下限加余量, 不超过高亮上限,
    压在上面的字不低于口径(编辑区按 高亮上的字, 输入框按 输入框选中的字). 已达标的不动; selection.background 原主题未定义时
    沿用编辑区选区的色相. 先按惯常方向(浅色主题往深, 深色主题往亮)找, 字读不清时改往反方向(远离字色, 字反而更清楚)."""
    bg, fg = t['bg'], t['fg']
    if 'editor.selectionBackground' not in colors:
        return
    colors.setdefault('selection.background', colors['editor.selectionBackground'])
    inp, _, itext = input_selection(colors, bg)
    vis_lo, vis_hi = SELECTION_VISIBLE[0] + 0.08, math.inf
    # 选区上的字按高亮底上的字的可读口径(3.5)判: 原选区上的字只要读得清就保留原选区, 不为凑 4.5 把选区压成近黑(如 Sunlit Dark)
    for k, under, text, tmin in (('editor.selectionBackground', bg, fg, HIGHLIGHT_TEXT_MIN + 0.05),
                                 ('selection.background', inp, itext, INPUT_SELECTION_TEXT[1] + 0.05)):
        rgb, alpha = parse(colors[k])
        cur = blend(rgb, under, int(alpha, 16) / 255 if alpha else 1.0)
        if vis_lo - 0.08 <= cr(cur, under) <= vis_hi and cr(text, cur) >= tmin - 0.05:
            continue
        # 先从原选区色出发只动必要的一侧: 看不出就远离底色, 字读不清就远离字色; 两者兼顾不了再按下面从底色重算
        if cr(text, cur) >= tmin - 0.05:
            c = away(cur, under, vis_lo)
            if cr(text, c) >= tmin - 0.05 and cr(c, under) <= vis_hi:
                colors[k] = hx(c)
                continue
        elif cr(cur, under) >= vis_lo - 0.08:
            c = away(cur, text, tmin)
            if vis_lo - 0.08 <= cr(c, under) <= vis_hi:
                colors[k] = hx(c)
                continue
        _, C, H = oklch(cur)
        Lu = oklch(under)[0]
        # best: 看得出且字可读; most: 字可读的前提下最看得出的一档(正文本身偏淡, 如 Sunlit Light 4.56, 两者兼顾不了时退而用它)
        best, most = None, cur
        for sign in ((-1, 1) if lum(under) > 0.2 else (1, -1)):
            for i in range(1, 120):
                L = Lu + sign * i * 0.004
                if not 0 < L < 1:
                    break
                c = from_oklch(L, C, H)
                if cr(text, c) < tmin or cr(c, under) > vis_hi:
                    break
                if cr(c, under) > cr(most, under) or cr(text, most) < tmin - 0.05:
                    most = c
                if cr(c, under) >= vis_lo:
                    best = c
                    break
            if best is not None:
                break
        if best is not None:
            colors[k] = hx(best)
        elif hx(most) != hx(cur):
            colors[k] = hx(most)


def highlight_text_floor(colors: dict, t: dict) -> None:
    # 选区, 查找等高亮底上的正文不低于 HIGHLIGHT_TEXT_MIN(留 0.03 余量防 hex 取整): 半透明的降透明度, 不透明的沿远离正文的方向调明度
    if not on('highlight_text'):
        return
    bg, fg = t['bg'], t['fg']
    for k in HIGHLIGHT_KEYS:
        p = parse(colors.get(k))
        if p is None:
            continue
        rgb, alpha = p
        a = int(alpha, 16) / 255 if alpha else 1.0
        bad = lambda c, a: cr(fg, blend(c, bg, a)) < HIGHLIGHT_TEXT_MIN + 0.03
        if not bad(rgb, a):
            continue
        if alpha:
            while a > 0.05 and bad(rgb, a):
                a -= 0.02
            alpha = '%02X' % round(a * 255)
        else:
            L, C, H = oklch(rgb)
            step = 0.004 if oklch(bg)[0] > L else -0.004
            while bad(rgb, 1.0) and 0 < L < 1:
                L += step
                rgb = from_oklch(L, C, H)
        colors[k] = hx(rgb) + alpha


# 查找当前要比其他匹配醒目: 与编辑区底的色差至少大 FIND_GAP_DE(Owl Light 原先两者同色, Pale 的当前反而更淡);
# 不足时先把当前往远离底色挪明度, 到高亮口径边界仍不够再把其他匹配往底色收, 但其他匹配的色差不低于 FIND_OTHER_MIN_DE
FIND_GAP_DE, FIND_OTHER_MIN_DE = 5, 5


def find_order(colors: dict, t: dict) -> None:
    bg, fg = t['bg'], t['fg']
    keys = 'editor.findMatchBackground', 'editor.findMatchHighlightBackground'
    ps = [parse(colors.get(k)) for k in keys]
    if None in ps:
        return
    (c, calpha), (o, oalpha) = ps
    ca, oa = (int(x, 16) / 255 if x else 1.0 for x in (calpha, oalpha))
    de = lambda x, a: de2000(blend(x, bg, a), bg)
    short = lambda: de(c, ca) < de(o, oa) + FIND_GAP_DE
    ok = lambda x, a: not on('highlight_text') or cr(fg, blend(x, bg, a)) >= HIGHLIGHT_TEXT_MIN + 0.03
    if not short():
        return
    L, C, H = oklch(c)
    away = -0.004 if oklch(bg)[0] > 0.5 else 0.004
    while short() and 0 < L + away < 1:
        nxt = from_oklch(L + away, C, H)
        if not ok(nxt, ca):
            break
        L, c = L + away, nxt
    colors[keys[0]] = hx(c) + calpha
    if oalpha:
        while short() and oa > 0.06 and de(o, oa - 0.02) >= FIND_OTHER_MIN_DE:
            oa -= 0.02
        colors[keys[1]] = hx(o) + '%02X' % round(oa * 255)
    else:
        L, C, H = oklch(o)
        while short() and de(from_oklch(L - away, C, H), 1.0) >= FIND_OTHER_MIN_DE:
            L -= away
            o = from_oklch(L, C, H)
        colors[keys[1]] = hx(o)


def away(c: Rgb, ref: Rgb, goal: float) -> Rgb:
    """c 沿远离 ref 的方向调明度(比 ref 亮就更亮, 暗就更暗), 色相与饱和度不变, 直到对比度 >= goal 或到头;
    与 fit 不同, 方向按两者的相对明暗定, 不按 ref 是不是暗色(中等亮度的彩色底上的白字也往白推)."""
    L, _, H = oklch(c)
    s, step, out = sat(c), (0.004 if lum(c) >= lum(ref) else -0.004), c
    while cr(out, ref) < goal and 0 < L + step < 1:
        L += step
        out = with_sat(L, s, H)
    return out


def white_cap(colors: dict) -> None:
    """深色主题里近纯白的界面前景(字, 图标, 线)压到明度 0.88(colorlib.unwhite); 底色类键与阴影不动; 终端 16 色已在 themes.py 压过, 这里再遇到不会变."""
    for k, v in list(colors.items()):
        p = parse(v)
        if p is None or 'shadow' in k.lower() or re.search(r'(?i)background$', k) or levels.doc()['keyLevels'].get(k, '').startswith('底色'):
            continue
        new = unwhite(p[0])
        if new != p[0]:
            colors[k] = hx(new) + p[1]


def transform(t: dict, src: dict) -> dict:
    m = Mapper(t, src)
    colors = {}
    for k, v in src['colors'].items():
        out = m.token(v) if k.startswith(TEXT_ON_CODE) else m.ui(v)
        if out is not None:
            colors[k] = out
    # 编辑区底色 / 正文 / 光标, 终端选区与 16 色按 themes.py 的结果写回; 与补全段产物相同的不动(保留原写法)
    put = lambda k, c: colors.__setitem__(k, hx(c)) if parse(colors.get(k)) is None or hx(opaque(colors, k, t['bg'])) != hx(c) else None
    for k, c in (('editor.background', t['bg']), ('editor.foreground', t['fg']), ('editorCursor.foreground', t['cursor'])):
        put(k, c)
    if t.get('sel_changed'):
        colors['terminal.selectionBackground'], colors['terminal.inactiveSelectionBackground'] = hx(t['sel']), hx(t['sel_inactive'])
    for n in ANSI:
        put('terminal.ansi' + n, t['ansi'][n])
        put('terminal.ansiBright' + n, t['ansi']['Bright' + n])
    # themes.py 按编辑区底提终端彩色; VS Code 终端画在 terminal.background 上(如 Ayu / Owl Light 比编辑区底深一档), 按它再补一次
    tbg = opaque(colors, 'terminal.background', t['bg'])
    if on('term_floor') and tbg is not None and hx(tbg) != hx(t['bg']):
        for k in [p + n for p in ('terminal.ansi', 'terminal.ansiBright') for n in ANSI[1:7]]:
            c = opaque(colors, k, tbg)
            if c is not None and cr(c, tbg) < LEGIBLE + TERM_MARGIN:
                colors[k] = hx(fit(c, tbg, lo=LEGIBLE + TERM_MARGIN))

    highlight_text_floor(colors, t)
    if on('find_order'):
        find_order(colors, t)
    if on('white_cap') and t['dark']:
        white_cap(colors)
    # 分层门槛: 界面文字, 徽标 / 按钮 / 列表选中行上的字, 焦点描边, 占位字等的下限; 放在选区之前, 选区按调整后的输入框字色求
    if on('level_floor'):
        levels.fix(colors, t, (WHITE_L - 0.01, WHITE_C) if on('white_cap') and t['dark'] else None)
    # 输入框底色与文字在前面几步还会调整, 选区放到它们之后求
    if on('selections'):
        selections(colors, t)

    # 语法规则与语义色: 补全段已按规则池补齐, 这里只调色
    rules = source_rules(src, m)
    semantic = {}
    for k, v in (src.get('semanticTokenColors') or {}).items():
        if isinstance(v, str):
            v = m.token(v)
        elif isinstance(v, dict) and v.get('foreground'):
            v = dict(v, foreground=m.token(v['foreground']))
        if v:
            semantic[k] = v
    if on('white_cap') and t['dark']:
        cap = lambda v: (lambda p: hx(unwhite(p[0])) + p[1] if p else v)(parse(v))
        for r in rules:
            if isinstance(r.get('settings'), dict) and r['settings'].get('foreground'):
                r['settings']['foreground'] = cap(r['settings']['foreground'])
        for k, v in semantic.items():
            semantic[k] = cap(v) if isinstance(v, str) else dict(v, foreground=cap(v['foreground'])) if isinstance(v, dict) and v.get('foreground') else v
    if on('syntax_separate'):
        rules = separate.fix(rules, src, t, is_comment_rule)
    conform(colors, rules, semantic, t)
    return dict(colors=dict(sorted(colors.items())), tokenColors=rules, semanticTokenColors=semantic)


def is_comment_rule(rule: dict) -> bool:
    """规则按注释口径处理. 补全段按角色成组的规则(name 为 'Pool <角色>')看角色: 组里混有 comment.block.documentation variable
    这类选择器, 按选择器判会让整组变量色只抬到 3.4(如 Sunlit 的 Pool variable #268BD2 停在 3.41); 原主题自己的规则仍按选择器里
    出现 comment 判(含 punctuation.definition.comment 与 comment markup.link 这类注释里的片段, 原主题给的就是注释色)."""
    name = rule.get('name') or ''
    if name.startswith('Pool '):
        return name == 'Pool comment'
    return any('comment' in x for x in scopes_of(rule))


def source_rules(src: dict, m: 'Mapper') -> list[dict]:
    """沿用原主题的 tokenColors(选择器, 字体样式不变), 只把各条的前景色经 Mapper.token 调色(注释走注释口径)."""
    out = []
    for r in json.loads(json.dumps(src.get('tokenColors', []))):
        st = r.get('settings')
        if isinstance(st, dict) and st.get('foreground'):
            v = m.token(st['foreground'], comment=is_comment_rule(r))
            # 非 hex 的写法(如 inherit)VS Code 不认, 按 schema 丢掉
            if v:
                st['foreground'] = v
            else:
                del st['foreground']
        out.append(r)
    return out


def render(t: dict) -> dict:
    # 输入是补全段的中间主题 <name>-full.json(complete.py), 不是原主题
    src = load(os.path.join(FULL, t['full']))
    body = transform(t, src)
    return {
        '$schema': 'vscode://schemas/color-theme',
        'name': t['label'],
        'type': 'dark' if t['dark'] else 'light',
        'semanticHighlighting': src.get('semanticHighlighting', True),
        'colors': body['colors'],
        'tokenColors': body['tokenColors'],
        'semanticTokenColors': body.get('semanticTokenColors') or {},
    }


def identity() -> int:
    if os.environ.get('COMFORT_STEPS') != 'none':
        print('--identity 要在 COMFORT_STEPS=none 下运行')
        return 2
    bad = []
    for t in build():
        full, out = load(os.path.join(FULL, t['full'])), render(t)
        for k in ('colors', 'tokenColors', 'semanticTokenColors'):
            a, b = full.get(k) or {}, out[k] or {}
            if a != b:
                diff = [x for x in set(a) | set(b) if a.get(x) != b.get(x)] if isinstance(a, dict) else [f'{len(a)} 条 vs {len(b)} 条']
                bad.append(f"{t['name']} {k}: {len(diff)} 处不同, 例 {sorted(map(str, diff))[:3]}")
    print('全关产物与 full 逐键相等' if not bad else '全关产物与 full 不等(有未登记的改色):\n  ' + '\n  '.join(bad))
    return 1 if bad else 0


def main() -> int:
    if '--identity' in sys.argv:
        return identity()
    check = '--check' in sys.argv
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else OUT
    os.makedirs(out, exist_ok=True)
    stale = []
    for t in build():
        path = os.path.join(out, f"{t['name']}.json")
        theme = render(t)
        bad = problems(theme)
        if bad:
            print(f"{t['name']}: 生成结果不符合 vscode://schemas/color-theme:", *bad[:10], sep='\n  ')
            return 1
        text = json.dumps(theme, indent='\t', ensure_ascii=False) + '\n'
        old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if check:
            if old != text:
                stale.append(os.path.relpath(path, ROOT))
        elif old != text:
            open(path, 'w', encoding='utf-8').write(text)
            print('wrote', os.path.relpath(path, ROOT))
    if stale:
        print('与 tools/gen/themes.py 不一致, 先运行 uv run tools/gen/gen_vscode.py:', *stale, sep='\n  ')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
