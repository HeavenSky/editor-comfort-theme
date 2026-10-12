# /// script
# requires-python = ">=3.11"
# ///
# 由 themes.py, tools/sources/ 下的原主题与 VS Code 颜色注册表生成 VS Code 颜色主题 themes/<name>-color-theme.json.
# 用法: uv run tools/gen_vscode.py [--check]   (--check: 只比对, 产物与生成结果不一致时退出码 1)
import json, math, os, re, sys

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import Rgb, blend, cr, from_oklch, h, hx, lum, oklch, toward_bg, tune
import pool
from coverage import fill as fill_coverage
from schema import FONT_STYLE, HEX, RULE_KEYS, SEMANTIC_STYLE_KEYS, SETTINGS_KEYS, TRANSPARENT, problems
from comfort import (BADGE_MAX_CR, BADGE_PAIRS, BADGE_TEXT_MIN, BORDER_KEYS, BORDER_MAX_CR, CONTROL_BORDER_KEYS, CONTROL_BORDER_MAX_CR,
                     CONTROL_TEXT_MIN, CONTROL_TEXT_PAIRS, FOCUS_KEYS, FOCUS_MAX, FOCUS_MIN_CR, GRAY_CHROMA, TINT_KEYS, TINTED_BG_CHROMA, PLACEHOLDER_CR, PLACEHOLDER_KEY, PLACEHOLDER_MAX_CHROMA,
                     HIGHLIGHT_KEYS, HIGHLIGHT_MAX_CR,
                     HIGHLIGHT_TEXT_MIN, LIGHT_PANEL_MAX, PANEL_KEYS,
                     PANEL_MAX_CHROMA, PANEL_MAX_CR, UI_TEXT_MAX, UI_TEXT_SKIP, own_background)
from themes import ANSI, build

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources')
REGISTRY = os.path.join(SOURCES, 'vscode-color-registry.json')
OUT = os.path.join(ROOT, 'themes')

# 界面上的文字与其底色, 及对比度下限; metrics.py 用同一张表评级
UI_PAIRS = [
    ('editorLineNumber.foreground', 'editor.background', 2.2),
    ('sideBar.foreground', 'sideBar.background', 4.5),
    ('tab.activeForeground', 'tab.activeBackground', 4.5),
    ('tab.inactiveForeground', 'tab.inactiveBackground', 4.5),
    ('statusBar.foreground', 'statusBar.background', 4.5),
    ('activityBar.foreground', 'activityBar.background', 4.5),
    ('activityBar.inactiveForeground', 'activityBar.background', 4.5),
    ('sideBarTitle.foreground', 'sideBar.background', 4.5),
    ('sideBarSectionHeader.foreground', 'sideBarSectionHeader.background', 4.5),
    ('titleBar.activeForeground', 'titleBar.activeBackground', 4.5),
    # 没有定义 sideBar.foreground 的主题(如 Ayu)文件树用通用前景色
    ('foreground', 'sideBar.background', 4.5),
]
# 按钮(如源代码管理的 Commit): 低彩度, 与编辑区底拉开到 BUTTON_CR(悬停再高一点), 不做饱和的实心色块, 也不至于看不出是按钮
BUTTON_PAIRS = [('button.background', 1.75), ('button.hoverBackground', 2.0)]
BUTTON_CHROMA = 0.06
# 列表选中 / 悬停 / 聚焦行上的字: 用正文色, 不用彩色(彩色像报错或链接)
LIST_TEXT_KEYS = ['list.activeSelectionForeground', 'list.inactiveSelectionForeground', 'list.focusForeground', 'list.hoverForeground',
                  'list.focusHighlightForeground']
# 行号对比度上限: 常驻视野边缘, 够读即可(防疲劳理想 2.0~2.6)
LINE_NO_MAX = 2.6
# 画在代码上的界面色, 按语法色的规则调色
TEXT_ON_CODE = ('editorBracketHighlight.foreground',)
# 原主题不定义括号色时, 用原主题的 数字 / 关键字 / 转义 色补上, 而不是落到注册表的通用补色
BRACKET_FALLBACK = ['constant.numeric', 'keyword.control', 'constant.character.escape']
NEUTRAL_CHROMA = 0.035
SAME_COLOR = 0.012
COMMENT_RATIO = 1.85
COMMENT_RANGE = (3.4, 4.2)


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
    """把原主题的颜色映射到目标主题: 语法色调对比度与彩度, 界面中性色随底色平移, 界面彩色封顶彩度."""

    def __init__(self, t: dict, src: dict):
        self.t = t
        c = src['colors']
        self.src_bg = parse(c['editor.background'])[0]
        self.src_fg = parse(source_fg(src, t['dark']))[0]
        self.dl = oklch(t['bg'])[0] - oklch(self.src_bg)[0]
        normal = [t['ansi'][n] for n in ANSI[1:7]]
        self.hues = [(oklch(c)[2], c) for c in normal]
        # 注释对比度: 'auto' 随正文联动, 正文 / COMMENT_RATIO, 限制在 COMMENT_RANGE 内
        target = t.get('comment_cr')
        if target == 'auto':
            target = min(COMMENT_RANGE[1], max(COMMENT_RANGE[0], cr(t['fg'], t['bg']) / COMMENT_RATIO))
        self.comment_cr = target

    def token(self, v, comment: bool = False) -> str | None:
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        if dist(rgb, self.src_fg) < SAME_COLOR and not alpha:
            return hx(self.t['fg'])
        if alpha:
            # 半透明语法色(原主题用来弱化标点)按叠到底色上的实际颜色调对比度, 输出不透明色
            base = self.t['fg'] if dist(rgb, self.src_fg) < SAME_COLOR else rgb
            rgb, alpha = blend(base, self.t['bg'], int(alpha, 16) / 255), ''
        bg = self.t['bg']
        if comment:
            if self.comment_cr is None:
                return hx(rgb) + alpha
            # 注释统一到同一对比度: 偏低的提上来, 偏高的压下去
            return hx(toward_bg(tune(hx(rgb), bg, 0.04, self.comment_cr), bg, self.comment_cr)) + alpha
        out = tune(hx(rgb), bg, self.t['syn_cap'], self.t['token_min'])
        if self.t.get('syntax_max'):
            # 语法色不亮过正文太多, 避免满屏最抢眼的是字符串一类的彩色
            out = toward_bg(out, bg, cr(self.t['fg'], bg) * self.t['syntax_max'])
        return hx(out) + alpha

    def ui(self, v, ref_bg: Rgb | None = None) -> str | None:
        # ref_bg: 该颜色所在体系的编辑区底; 原主题的颜色用原主题底, VS Code 默认色用 VS Code 默认主题的底
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        ref_bg = ref_bg or self.src_bg
        if dist(rgb, ref_bg) < SAME_COLOR:
            return hx(self.t['bg']) + alpha
        if ref_bg is self.src_bg and dist(rgb, self.src_fg) < SAME_COLOR:
            return hx(self.t['fg']) + alpha
        L, C, H = oklch(rgb)
        if C < NEUTRAL_CHROMA:
            return hx(from_oklch(L + oklch(self.t['bg'])[0] - oklch(ref_bg)[0], C, H)) + alpha
        return hx(from_oklch(L, min(C, self.t['cap']), H)) + alpha

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
        # 背景类默认色: 色相取本主题同色相的终端色, 明度保留默认值(随底色平移), 彩度封顶; 不把暗底色换成亮色块
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        L, C, H = oklch(rgb)
        if C < NEUTRAL_CHROMA:
            return None
        near = min(self.hues, key=lambda x: abs(math.atan2(math.sin(x[0] - H), math.cos(x[0] - H))))
        L += oklch(self.t['bg'])[0] - oklch(ref_bg)[0]
        return hx(from_oklch(L, min(C, self.t['cap']), oklch(near[1])[2])) + alpha


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
        if k.startswith(TEXT_ON_CODE):
            out = m.token(default)
        elif k.lower().endswith('background'):
            out = m.tint(default, vs_bg)
        else:
            out = m.accent(default)
        colors[k] = out or m.ui(default, vs_bg)


def calm(colors: dict, t: dict) -> None:
    # 面板底色不成亮块, 高亮底色不刺眼且压在上面的正文可读; 口径与 comfort.py 的防疲劳规则一致
    bg, fg = t['bg'], t['fg']
    for k in PANEL_KEYS + HIGHLIGHT_KEYS:
        p = parse(colors.get(k))
        if p is None:
            continue
        rgb, alpha = p
        a = int(alpha, 16) / 255 if alpha else 1.0
        limit = PANEL_MAX_CR if k in PANEL_KEYS else HIGHLIGHT_MAX_CR
        # 留 0.03 余量, 避免 hex 取整后又越过门禁边界
        # 浅色主题的大面积底色另有亮度上限(LIGHT_PANEL_MAX): 比编辑区底更亮的输入框, 弹窗等像一块块白纸
        bright = lambda c, a: not t['dark'] and k in PANEL_KEYS and lum(blend(c, bg, a)) > LIGHT_PANEL_MAX - 0.01
        bad = lambda c, a: cr(blend(c, bg, a), bg) > limit - 0.03 or bright(c, a) or (
            k in HIGHLIGHT_KEYS and cr(fg, blend(c, bg, a)) < HIGHLIGHT_TEXT_MIN + 0.03)
        if bad(rgb, a):
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
        # 彩度在对比度之后压: 降透明度会让底色占比变大, 底色自身的彩度随之透出来
        chroma = lambda c: oklch(blend(c, bg, a))[1]
        if k in PANEL_KEYS and chroma(rgb) > PANEL_MAX_CHROMA:
            # 半透明色叠到底色上后的彩度与自身彩度不成比例, 二分自身彩度, 让叠色结果落在上限内(留余量防 hex 取整越界)
            L, C, H = oklch(rgb)
            lo, hi = 0.0, C
            for _ in range(30):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if chroma(from_oklch(L, mid, H)) <= PANEL_MAX_CHROMA - 0.002 else (lo, mid)
            rgb = from_oklch(L, lo, H)
            # 中性灰半透明叠在带色底上, sRGB 混色后仍可能带出底色的彩度; 此时往底色的反色相补一点彩度抵消
            if chroma(rgb) > PANEL_MAX_CHROMA - 0.002:
                rgb = min((from_oklch(L, i / 500, oklch(bg)[2] + math.pi) for i in range(51)), key=chroma)
            # 改彩度会带动亮度, 再沿底色方向收明度, 不让面板因此越过亮块上限
            L, C, H = oklch(rgb)
            step = 0.004 if oklch(bg)[0] > L else -0.004
            while bad(rgb, a) and 0 < L < 1:
                L += step
                rgb = from_oklch(L, C, H)
            colors[k] = hx(rgb) + alpha


# 徽标的生成目标比门禁(BADGE_MAX_CR 2.2, 字 >= 3.5)更安静: 低彩度的色点, 与编辑区底对比度 BADGE_SOFT_CR 以内, 字推到 BADGE_TEXT_GOAL;
# 贴着门禁上限时浅色主题是一片粉彩色块, 上面的深色字只有 3.7, 深色主题的字只有 3.6
BADGE_CHROMA, BADGE_SOFT_CR, BADGE_TEXT_GOAL = 0.07, 1.7, 4.5


def quiet_badges(colors: dict, t: dict) -> None:
    # 徽标: 压到 BADGE_SOFT_CR 以内, 深色主题不成亮块, 浅色主题不成暗斑; 字取与徽标反差大的一侧(暗徽标配浅字, 亮徽标配深字), 推到可读
    bg, dark = t['bg'], t['dark']
    for bk, fk in BADGE_PAIRS:
        badge = opaque(colors, bk, bg)
        if badge is None:
            continue
        L, C, H = oklch(badge)
        if C > BADGE_CHROMA:
            badge = from_oklch(L, BADGE_CHROMA, H)
        if cr(badge, bg) > BADGE_SOFT_CR:
            badge = toward_bg(badge, bg, BADGE_SOFT_CR)
        # 亮度 0.18 附近白字与黑字对徽标的对比度相等; 字从正文(深色主题浅字)或底色一侧起步, 不额外提亮或加黑
        light = lum(badge) < 0.18
        text = (t['fg'] if dark else t['bg']) if light else (t['bg'] if dark else t['fg'])
        step = 0.004 if light else -0.004
        # 先把徽标往远离字的方向调(深色主题即再压暗); 靠近编辑区底时最多到面板上限, 免得徽标看不出来
        L, C, H = oklch(badge)
        toward = (-step > 0) == (oklch(bg)[0] > L)
        while cr(text, badge) < BADGE_TEXT_GOAL + 0.03 and 0 < L - step < 1 and not (toward and cr(badge, bg) < PANEL_MAX_CR + 0.1):
            L -= step
            badge = from_oklch(L, C, H)
        L, C, H = oklch(text)
        while cr(text, badge) < BADGE_TEXT_GOAL + 0.03 and 0 < L + step < 1:
            L += step
            text = from_oklch(L, C, H)
        colors[bk], colors[fk] = hx(badge), hx(text)


def quiet_buttons(colors: dict, t: dict) -> None:
    """按钮底: 彩度封顶 BUTTON_CHROMA, 明度从编辑区底向外推到 BUTTON_PAIRS 给的对比度(色相不变); 字从正文起步推到 4.5."""
    bg, fg = t['bg'], t['fg']
    for key, target in BUTTON_PAIRS:
        c = opaque(colors, key, bg)
        if c is None:
            continue
        L, C, H = oklch(c)
        C = min(C, BUTTON_CHROMA)
        L = oklch(bg)[0]
        step = 0.004 if t['dark'] else -0.004
        b = from_oklch(L, C, H)
        while cr(b, bg) < target and 0 < L < 1:
            L += step
            b = from_oklch(L, C, H)
        colors[key] = hx(b)
    under = parse(colors.get('button.background'))
    if under:
        colors['button.foreground'] = hx(tune(hx(fg), under[0], 1.0, 4.55))


def quiet_lists_and_borders(colors: dict, t: dict, m: 'Mapper') -> None:
    """列表选中行的字用正文色; 布局边框去掉彩度; 被忽略文件(.gitignore 命中)按注释的对比度显示: 看得出变淡, 也仍然读得清."""
    bg, fg = t['bg'], t['fg']
    for k in LIST_TEXT_KEYS:
        p = parse(colors.get(k))
        if p and oklch(p[0])[1] > NEUTRAL_CHROMA:
            colors[k] = hx(fg) + p[1]
    for k in BORDER_KEYS:
        p = parse(colors.get(k))
        if p and oklch(p[0])[1] > PANEL_MAX_CHROMA:
            L, C, H = oklch(p[0])
            colors[k] = hx(from_oklch(L, PANEL_MAX_CHROMA, H)) + p[1]
        # 只需看得出分界: 与编辑区底的对比度压到 BORDER_MAX_CR(如 Dracula 的拆分线原本 6.5, 一道亮线贯穿屏幕)
        p = parse(colors.get(k))
        if p is None:
            continue
        rgb, alpha = p
        a = int(alpha, 16) / 255 if alpha else 1.0
        if cr(blend(rgb, bg, a), bg) > BORDER_MAX_CR:
            if alpha:
                while a > 0.05 and cr(blend(rgb, bg, a), bg) > BORDER_MAX_CR - 0.02:
                    a -= 0.02
                colors[k] = hx(rgb) + '%02X' % round(a * 255)
            else:
                colors[k] = hx(toward_bg(rgb, bg, BORDER_MAX_CR - 0.02))
    k = 'gitDecoration.ignoredResourceForeground'
    p = parse(colors.get(k))
    if p and m.comment_cr:
        under = opaque(colors, 'sideBar.background', bg) or bg
        c = blend(p[0], under, int(p[1], 16) / 255) if p[1] else p[0]
        # 比普通文件名(侧边栏前景)至少暗一档, 否则看不出被忽略
        normal = opaque(colors, 'sideBar.foreground', under) or opaque(colors, 'foreground', under)
        target = min(m.comment_cr, cr(normal, under) * 0.75) if normal else m.comment_cr
        colors[k] = hx(toward_bg(tune(hx(c), under, 0.04, target), under, target))


def quiet_ui_text(colors: dict, t: dict) -> None:
    # 界面文字与图标不比正文更刺眼(口径见 comfort.ui_text_glare); 彩色小块(按钮, 徽标)上的字不在此列
    bg = t['bg']
    limit = cr(t['fg'], bg) * UI_TEXT_MAX
    for k in list(colors):
        if not k.lower().endswith('foreground') or k.startswith(UI_TEXT_SKIP):
            continue
        under, colored = own_background(colors, k, bg)
        p = parse(colors[k])
        if colored or p is None:
            continue
        rgb, alpha = p
        a = int(alpha, 16) / 255 if alpha else 1.0
        if cr(blend(rgb, under, a), under) <= limit:
            continue
        if alpha:
            while a > 0.05 and cr(blend(rgb, under, a), under) > limit - 0.02:
                a -= 0.02
            colors[k] = hx(rgb) + '%02X' % round(a * 255)
        else:
            colors[k] = hx(toward_bg(rgb, under, limit - 0.02))


def cap_cr(colors: dict, k: str, under: Rgb, limit: float) -> None:
    """k 的颜色与 under 的对比度压到 limit 以内: 半透明色降透明度, 不透明色朝底色收明度, 色相不变."""
    p = parse(colors.get(k))
    if p is None:
        return
    rgb, alpha = p
    a = int(alpha, 16) / 255 if alpha else 1.0
    if cr(blend(rgb, under, a), under) <= limit:
        return
    if alpha:
        while a > 0.05 and cr(blend(rgb, under, a), under) > limit - 0.02:
            a -= 0.02
        colors[k] = hx(rgb) + '%02X' % round(a * 255)
    else:
        colors[k] = hx(toward_bg(rgb, under, limit - 0.02))


def tint_grays(colors: dict, t: dict) -> None:
    # 底色带色调的主题里, 中间灰的底色块(多为 VS Code 默认色补出, 如活动栏 / 工具栏选中图标的底, 列表失焦选中行)换成底色的色调:
    # 色相取编辑区底, 彩度取底色彩度(封顶 PANEL_MAX_CHROMA), 明度与透明度不变; 口径见 comfort.gray_patches
    L0, C0, H0 = oklch(t['bg'])
    if C0 <= TINTED_BG_CHROMA:
        return
    for k in TINT_KEYS:
        p = parse(colors.get(k))
        if p is None:
            continue
        rgb, alpha = p
        L, C, H = oklch(rgb)
        a = int(alpha, 16) / 255 if alpha else 1.0
        if C < GRAY_CHROMA and 0.12 < L < 0.92 and a >= 0.2:
            colors[k] = hx(from_oklch(L, min(C0, PANEL_MAX_CHROMA - 0.002), H0)) + alpha


def quiet_controls(colors: dict, t: dict) -> None:
    # 输入框 / 下拉框(问题面板与输出面板的筛选框, 输出通道下拉框等): 描边去彩度并压到 CONTROL_BORDER_MAX_CR, 焦点描边不超过 正文 x FOCUS_MAX;
    # 占位提示字落到 PLACEHOLDER_CR(注释口径, 比输入的字淡), 输入的字至少 CONTROL_TEXT_MIN; 口径见 comfort.control_issues
    bg, fg = t['bg'], t['fg']
    inp = opaque(colors, 'input.background', bg) or bg
    for k in CONTROL_BORDER_KEYS:
        p = parse(colors.get(k))
        if p and oklch(p[0])[1] > PANEL_MAX_CHROMA:
            L, C, H = oklch(p[0])
            colors[k] = hx(from_oklch(L, PANEL_MAX_CHROMA, H)) + p[1]
        cap_cr(colors, k, bg, CONTROL_BORDER_MAX_CR)
    for k in FOCUS_KEYS:
        cap_cr(colors, k, bg, cr(fg, bg) * FOCUS_MAX)
        # 太淡时提到 FOCUS_MIN_CR(半透明色先叠成不透明), 色相不变: 否则聚焦的输入框反而比未聚焦的描边更暗(如 Owl / Pale 的焦点描边 1.0)
        c = opaque(colors, k, bg)
        if c is not None and cr(c, bg) < FOCUS_MIN_CR:
            colors[k] = hx(tune(hx(c), bg, t['cap'], FOCUS_MIN_CR + 0.02))
    ph = opaque(colors, PLACEHOLDER_KEY, inp)
    if ph is not None:
        lo, hi = PLACEHOLDER_CR
        L, C, H = oklch(ph)
        if C > PLACEHOLDER_MAX_CHROMA:
            ph = from_oklch(L, PLACEHOLDER_MAX_CHROMA - 0.002, H)
            colors[PLACEHOLDER_KEY] = hx(ph)
        if cr(ph, inp) > hi:
            colors[PLACEHOLDER_KEY] = hx(toward_bg(ph, inp, hi - 0.02))
        elif cr(ph, inp) < lo:
            colors[PLACEHOLDER_KEY] = hx(tune(hx(ph), inp, 1.0, lo + 0.02))
    for fk, bk in CONTROL_TEXT_PAIRS:
        under = opaque(colors, bk, bg) or bg
        c = opaque(colors, fk, under)
        if c is not None and cr(c, under) < CONTROL_TEXT_MIN:
            colors[fk] = hx(tune(hx(c), under, 1.0, CONTROL_TEXT_MIN + 0.02))


# 源代码管理 Graph 视图的分支标签: 字是 historyItemHoverLabelForeground(默认取面板底), 底是各 ref 色(默认取 charts.blue / charts.purple)
GRAPH_LABEL_TEXT = 'scmGraph.historyItemHoverLabelForeground'
GRAPH_REF_KEYS = [('scmGraph.historyItemRefColor', 'charts.blue', 'editorInfo.foreground'),
                  ('scmGraph.historyItemRemoteRefColor', 'charts.purple'), ('scmGraph.historyItemBaseRefColor',)]
GRAPH_LABEL_MIN = 4.5


def graph_labels(colors: dict, t: dict) -> None:
    # 标签字回到 VS Code 的默认取色(面板底); 原主题沿用的浅灰字落在 ref 色块上几乎看不清, 如 One Dark Pro 的 #B1B1B1 字压在蓝底上.
    # ref 色与字不够 GRAPH_LABEL_MIN 时沿远离字色的方向推明度, 色相不变
    colors.pop(GRAPH_LABEL_TEXT, None)
    bg = opaque(colors, 'panel.background', t['bg']) or t['bg']
    for chain in GRAPH_REF_KEYS:
        ref = next((opaque(colors, k, bg) for k in chain if colors.get(k)), None)
        if ref is not None and cr(ref, bg) < GRAPH_LABEL_MIN:
            colors[chain[0]] = hx(tune(hx(ref), bg, t['cap'], GRAPH_LABEL_MIN))


def transform(t: dict, src: dict) -> dict:
    m = Mapper(t, src)
    colors = {}
    for k, v in src['colors'].items():
        out = m.token(v) if k.startswith(TEXT_ON_CODE) else m.ui(v)
        if out is not None:
            colors[k] = out
    if 'editorBracketHighlight.foreground1' not in colors:
        for i, scope in enumerate(BRACKET_FALLBACK, 1):
            colors[f'editorBracketHighlight.foreground{i}'] = m.token(resolve(src['tokenColors'], scope) or hx(m.src_fg))
    colors.update({
        'editor.background': hx(t['bg']), 'editor.foreground': hx(t['fg']), 'editorCursor.foreground': hx(t['cursor']),
        'terminal.background': hx(t['bg']), 'terminal.foreground': hx(t['fg']), 'terminalCursor.foreground': hx(t['cursor']),
    })
    for n in ANSI:
        colors['terminal.ansi' + n] = hx(t['ansi'][n])
        colors['terminal.ansiBright' + n] = hx(t['ansi']['Bright' + n])

    fill_hardcoded(colors, t, m)

    # 映射后仍可能有界面文字对比度不足(底色变了, 或原主题本身就偏淡), 逐对推到下限
    for fg_key, bg_key, need in UI_PAIRS:
        under = opaque(colors, bg_key, t['bg']) or t['bg']
        fg = opaque(colors, fg_key, under)
        if fg is not None and cr(fg, under) < need:
            colors[fg_key] = hx(tune(hx(fg), under, 1.0, need))
    line_no = opaque(colors, 'editorLineNumber.foreground', t['bg'])
    if line_no is not None and cr(line_no, t['bg']) > LINE_NO_MAX:
        colors['editorLineNumber.foreground'] = hx(toward_bg(line_no, t['bg'], LINE_NO_MAX))
    calm(colors, t)
    quiet_badges(colors, t)
    quiet_buttons(colors, t)
    quiet_lists_and_borders(colors, t, m)
    quiet_ui_text(colors, t)
    quiet_controls(colors, t)
    tint_grays(colors, t)
    graph_labels(colors, t)

    rules = pool_rules(src, m, t)
    # 语义着色交给 VS Code 内置的语义 token -> TextMate scope 映射, 与规则池一致; 原主题自带的语义色不再沿用
    semantic = {}
    # 统一着色覆盖: 原主题没定义的常用 scope 从本主题的相近角色取色补上(见 coverage.py)
    rules[:0] = fill_coverage(rules, hx(t['fg']))
    conform(colors, rules, semantic, t)
    return dict(colors=dict(sorted(colors.items())), tokenColors=rules, semanticTokenColors=semantic)


_POOL = None
VARIABLE_CHROMA = 0.09


def derive_variable(colors: dict, t: dict) -> str | None:
    """普通变量的派生专用色: 明度贴近参数色, 彩度 VARIABLE_CHROMA, 对比度在语法色下限与正文之间,
    在色环上取与周围角色色(pool.DERIVE_CONTEXT)最小色差最大的色相; 现成角色色都会与某个角色撞色, 所以单独派生."""
    from colorlib import de2000
    bg = t['bg']
    hi = cr(t['fg'], bg) * (t.get('syntax_max') or 1.0)
    ctx = [parse(colors[r])[0] for r in pool.DERIVE_CONTEXT if colors.get(r)]
    L0 = oklch(parse(colors['parameter'])[0])[0] if colors.get('parameter') else oklch(t['fg'])[0]
    best, pick = -1.0, None
    for dl in (0, -0.04, 0.04, -0.08, 0.08):
        for deg in range(0, 360, 3):
            c = from_oklch(L0 + dl, min(VARIABLE_CHROMA, t['syn_cap']), math.radians(deg))
            # 留 0.05 余量, 避免 hex 取整后越过对比度边界
            if not (t['token_min'] + 0.05 <= cr(c, bg) <= hi - 0.05):
                continue
            score = min(de2000(c, x) for x in ctx)
            if score > best:
                best, pick = score, c
    return hx(pick) if pick else None


# 属性名在样式表里成片出现, 色相取声明类型(复核时用户选定); 声明类型是近中性色时派生一个暗彩, 不借别的角色(借来必与那个角色撞色)
PROP_NAME_HUES = ['prop_name']
# 调色后撞色: 两个不同族角色 ΔE < CLASH_DE 而原主题里 ΔE >= APART_DE, 说明是调色(统一对比度, 封顶彩度)把它们挤到了一起
CLASH_DE, APART_DE, SEPARATE_DE = 5.0, 10.0, 6.0
SEPARATE_FIXED = {'text', 'comment', 'bold', 'italic'}


def muted_floor(colors: dict, t: dict) -> float:
    """暗彩的对比度: 语法色下限, 但不低于 5.0(清晰评"高"要求语法色 >= 5.0, 不为压暗个别选择器降掉整套主题的评级);
    本主题彩色语法色本就有低于 5.0 的(评级已是中高)时, 取它们的最低值, 免得暗彩反比正常色还亮."""
    bg = t['bg']
    crs = [cr(p[0], bg) for r in pool.ROLES if r not in pool.MUTED_SKIP and (p := parse(colors.get(r))) and oklch(p[0])[1] > NEUTRAL_CHROMA]
    return max(t['token_min'], min([5.0] + crs))


def dim_color(colors: dict, t: dict, hues: list[str], taken: list | None = None) -> str | None:
    """彩色但不抢眼: 取 hues 里第一个彩色的角色色, 明度压到 muted_floor(留 0.1 余量), 彩度不超过语法色上限;
    都是近中性色且给了 taken 时派生一个暗彩(见 derive_muted), 并记入 taken."""
    bg, floor = t['bg'], muted_floor(colors, t)
    for r in hues:
        p = parse(colors.get(r))
        if p and oklch(p[0])[1] > NEUTRAL_CHROMA:
            if cr(p[0], bg) <= floor + 0.1:
                return hx(p[0])
            return hx(tune(hx(toward_bg(p[0], bg, floor + 0.1)), bg, t['syn_cap'], floor))
    if taken is None:
        return None
    c = derive_muted(colors, t, floor, taken)
    taken.append(c)
    return hx(c)


def derive_muted(colors: dict, t: dict, floor: float, taken: list) -> Rgb:
    """派生暗彩: 对比度 muted_floor, 彩度为语法色上限, 色相取与周围角色色(含普通变量与已派生的暗彩)最小色差最大的方向;
    同一主题里多个近中性角色各派生一个, 互相避开, 不共用一个颜色."""
    from colorlib import de2000
    bg = t['bg']
    ctx = [parse(colors[r])[0] for r in pool.DERIVE_CONTEXT + ['variable'] if colors.get(r)] + taken
    best, pick = -1.0, None
    for deg in range(0, 360, 3):
        c = tune(hx(from_oklch(oklch(bg)[0], t['syn_cap'], math.radians(deg))), bg, t['syn_cap'], floor + 0.05)
        score = min(de2000(c, x) for x in ctx)
        if score > best:
            best, pick = score, c
    return pick


def separate(keyed: dict, src_colors: dict, t: dict, floor: float) -> None:
    """调色后撞色的两个不同族角色(见 CLASH_DE)沿明度拉开到 SEPARATE_DE: 按原主题的深浅顺序, 原本更醒目的一方提对比度,
    不够再把另一方压向底色; 可动范围是语法色下限到正文(深色主题再乘 syntax_max), 暗彩最多比暗彩下限高 0.8. 色相与彩度不变."""
    from colorlib import de2000
    bg = t['bg']
    hi_all = cr(t['fg'], bg) * (t.get('syntax_max') or 1.0)
    base = lambda k: k.split()[0]

    def bounds(k):
        lo = t['token_min'] + 0.05
        return (lo, min(hi_all, floor + 0.8) - 0.05) if k.endswith(' muted') else (lo, hi_all - 0.05)

    def push(k, up, other):
        c = parse(keyed[k])[0]
        L, C, H = oklch(c)
        lo, hi = bounds(k)
        step = (0.004 if t['dark'] else -0.004) * (1 if up else -1)
        while de2000(c, other) < SEPARATE_DE:
            n = from_oklch(L + step, C, H)
            if not (lo <= cr(n, bg) <= hi):
                break
            L, c = L + step, n
        keyed[k] = hx(c)

    def turn(k, other):
        c0 = parse(keyed[k])[0]
        L, C, H = oklch(c0)
        oc = parse(keyed[other])[0]
        rest = [parse(keyed[x])[0] for x in keys if x not in (k, other) and pool.FAMILY.get(base(x), base(x)) != pool.FAMILY.get(base(k), base(k))]
        best, pick = de2000(c0, oc), c0
        for deg in [d * s for d in range(2, 26, 2) for s in (1, -1)]:
            n = from_oklch(L, C, H + math.radians(deg))
            if any(de2000(n, x) < CLASH_DE for x in rest):
                continue
            score = de2000(n, oc)
            if score > best:
                best, pick = score, n
            if score >= SEPARATE_DE:
                break
        keyed[k] = hx(pick)

    # 近中性的角色也参与(两个原本不同的灰被挤成一样同样是撞色), 但正文, 注释这类基准色不动
    keys = [k for k in keyed if keyed[k] and src_colors.get(base(k))]
    for _ in range(4):
        moved = False
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                ra, rb = base(a), base(b)
                if ra == rb or pool.FAMILY.get(ra, ra) == pool.FAMILY.get(rb, rb) or (ra in SEPARATE_FIXED and rb in SEPARATE_FIXED):
                    continue
                # Markdown 角色只出现在文档里, 与代码角色不会同屏; 文档内部由 separate_markdown 分开
                if (ra in MARKDOWN_ROLES) != (rb in MARKDOWN_ROLES):
                    continue
                ca, cb = parse(keyed[a])[0], parse(keyed[b])[0]
                if de2000(ca, cb) >= CLASH_DE or de2000(src_colors[ra], src_colors[rb]) < APART_DE:
                    continue
                # 原主题里对比度高的一方仍更醒目
                strong, weak = (a, b) if cr(src_colors[ra], t['src_bg']) >= cr(src_colors[rb], t['src_bg']) else (b, a)
                # 正文, 注释等基准色(SEPARATE_FIXED)不动, 只移动另一方
                if base(strong) not in SEPARATE_FIXED:
                    push(strong, True, parse(keyed[weak])[0])
                if base(weak) not in SEPARATE_FIXED:
                    push(weak, False, parse(keyed[strong])[0])
                if de2000(parse(keyed[a])[0], parse(keyed[b])[0]) < SEPARATE_DE:
                    # 明度拉不开(暗彩可动范围窄, 或已到对比度边界): 暗彩一方优先, 否则较弱一方, 色相在 ±25° 内转开
                    mover = a if a.endswith(' muted') and not b.endswith(' muted') else b if b.endswith(' muted') else weak
                    if base(mover) in SEPARATE_FIXED:
                        mover = b if mover == a else a
                    turn(mover, b if mover == a else a)
                moved = True
        if not moved:
            break


# Markdown 专用角色, 按保留优先级排列: 原主题常让其中几个同色(如 Owl Light 的标题, 代码, 链接都是同一个蓝), 文档里挨着出现, 必须分开
MARKDOWN_ROLES = ['heading', 'link', 'raw', 'quote', 'bold', 'italic']
MARKDOWN_SAME_OK = {frozenset(('bold', 'italic'))}  # 粗体与斜体靠字形区分, 同色可接受


# 必须分开的角色对(保留, 转开): 样式表里属性名紧挨着属性值, 而属性名取的声明类型色在一些原主题里与常量同色(如 Monokai 的青);
# 两者逐行相邻, 色差要到 FORCED_DE 才看得出是两类东西(只转 20° 左右的同族色相肉眼仍是一种颜色)
FORCED_DE = 20.0
FORCED_APART = [('constant', 'prop_name')]


def turn_apart(keyed: dict, key: str, others: list, t: dict, goal: float = SEPARATE_DE + 4) -> None:
    """key 的颜色转色相(±90° 内), 与 others 的最小色差达到 goal; 达到的候选里取离本主题其余不同族颜色最远的,
    免得为了与 others 分开又撞上别的角色(如行内代码转到转义色). 都达不到时取与 others 最小色差最大者.
    明度与彩度不变, 对比度补回原值."""
    from colorlib import de2000
    c = parse(keyed[key])[0]
    L, C, H = oklch(c)
    fam = pool.FAMILY.get(key.split()[0], key)
    rest = [parse(v)[0] for k, v in keyed.items()
            if v and k != key and pool.FAMILY.get(k.split()[0], k) != fam and oklch(parse(v)[0])[1] > NEUTRAL_CHROMA]
    best, pick, ok = min(de2000(c, o) for o in others), c, None
    for deg in [d * s for d in range(4, 92, 4) for s in (1, -1)]:
        n = from_oklch(L, C, H + math.radians(deg))
        # 转色相会带动亮度; 对比度补回原值, 免得掉到语法色下限(或清晰评"高"的 5.0)以下
        if cr(n, t['bg']) < cr(c, t['bg']):
            n = tune(hx(n), t['bg'], t['syn_cap'], cr(c, t['bg']))
        score = min(de2000(n, o) for o in others)
        if score > best:
            best, pick = score, n
        if score >= goal:
            spare = min((de2000(n, o) for o in rest), default=99)
            if ok is None or spare > ok[0]:
                ok = (spare, n)
    keyed[key] = hx(ok[1] if ok else pick)


def separate_forced(keyed: dict, t: dict) -> None:
    from colorlib import de2000
    for keep, move in FORCED_APART:
        for k in (move, move + ' muted'):
            a, b = parse(keyed.get(keep)), parse(keyed.get(k))
            if a and b and de2000(a[0], b[0]) < FORCED_DE:
                turn_apart(keyed, k, [a[0]], t, FORCED_DE)


def separate_markdown(keyed: dict, t: dict) -> None:
    """Markdown 专用角色两两拉开到 SEPARATE_DE 以上(不看原主题是否同色): 优先级低的一方转色相(±90° 内取与前面各角色最小色差最大者),
    明度与彩度不变, 对比度基本不变. 近中性的(粗体 / 斜体常用正文色)不动, 也不参与比较."""
    from colorlib import de2000
    done = []
    # 暗彩变体(如列表符号是标题的暗彩, 链接文字是链接的暗彩)排在全部本色之后, 只与别的角色比, 不与自己的本色比
    for role in MARKDOWN_ROLES + [r + ' muted' for r in MARKDOWN_ROLES]:
        p = parse(keyed.get(role))
        if not p or oklch(p[0])[1] <= NEUTRAL_CHROMA:
            continue
        c = p[0]
        others = [parse(keyed[r])[0] for r in done
                  if frozenset((r.split()[0], role.split()[0])) not in MARKDOWN_SAME_OK and r.split()[0] != role.split()[0]]
        if others and min(de2000(c, o) for o in others) < SEPARATE_DE:
            turn_apart(keyed, role, others, t)
        done.append(role)


def plain(style: str | None) -> str:
    """去掉加粗, 保留斜体等; 结果为空串时显式写出, 免得继承到外层规则的加粗."""
    return ' '.join(x for x in (style or '').split() if x != 'bold')


def pool_rules(src: dict, m: 'Mapper', t: dict) -> list[dict]:
    """由规则池生成 tokenColors: 每个选择器按裁决出的角色取本主题的角色色(原主题的颜色经同样的调色), 设置相同的合为一条.
    暗彩选择器(见 pool.MUTED_*)单独成组: 本角色色的暗淡版本, 不加粗. 全部组的颜色定下后再拉开调色带来的撞色(separate)."""
    global _POOL
    if _POOL is None:
        _POOL = pool.build(build())
    src_rules = src.get('tokenColors', [])
    fg = source_fg(src, t['dark'])
    colors = {r: m.token(pool.role_value(src_rules, r, fg), comment=r == 'comment') for r in pool.ROLES}
    colors['variable'] = derive_variable(colors, t) or colors['variable']
    taken = []
    colors['prop_name'] = dim_color(colors, t, PROP_NAME_HUES, taken) or colors.get('prop_name')
    groups: dict[str, list[str]] = {}
    styles: dict[str, dict] = {}
    keyed: dict[str, str | None] = {}
    for sel, p in _POOL.items():
        role = p['role']
        if role == pool.INHERIT:
            continue
        key = role + ' muted' if p.get('muted') else role
        if key not in styles:
            style = '' if role in pool.PLAIN else pool.role_value(src_rules, role, None, 'fontStyle')
            color = colors.get(role)
            if p.get('muted'):
                color = dim_color(colors, t, [role], taken) or color
                style = plain(style)
            elif role == 'heading' and 'bold' not in (style or ''):
                # 标题靠加粗与正文分层; 原主题不加粗(如 Night Owl)时标题与正文常常同样亮, 分不出层级
                style = ' '.join(x for x in ((style or '') + ' bold').split())
            keyed[key] = color
            styles[key] = {} if style is None else {'fontStyle': style}
        groups.setdefault(key, []).append(sel)
    src_colors = {r: parse(pool.role_value(src_rules, r, fg) or '') for r in pool.ROLES}
    src_colors = {r: v[0] for r, v in src_colors.items() if v}
    # 派生色在原主题里没有对应颜色, 按其来源角色比
    src_colors['prop_name'] = src_colors.get('storage')
    separate(keyed, src_colors, dict(t, src_bg=m.src_bg), muted_floor(colors, t))
    separate_markdown(keyed, t)
    separate_forced(keyed, t)
    out = []
    for key, sels in groups.items():
        settings = ({'foreground': keyed[key]} if keyed[key] else {}) | styles[key]
        if settings:
            out.append({'name': f'Comfort {key}', 'scope': sels, 'settings': settings})
    return out


def render(t: dict) -> dict:
    src = load(os.path.join(SOURCES, t['source']))
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


def main() -> int:
    check = '--check' in sys.argv
    os.makedirs(OUT, exist_ok=True)
    stale = []
    for t in build():
        path = os.path.join(OUT, f"{t['name']}-color-theme.json")
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
        print('与 tools/themes.py 不一致, 先运行 uv run tools/gen_vscode.py:', *stale, sep='\n  ')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
