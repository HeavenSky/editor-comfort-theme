# 分层门槛: 读 assets/levels.json(tools/lab/threshold-lab.mjs export 生成), 按 颜色键 -> 级 与 颜色键 -> 实测底色键 的配对,
# 检查并修复低于修复下限 / 绝对下限的界面颜色; 调色步骤 level_floor(gen_vscode.py)与分层门禁(metrics.py)共用这一份口径.
# 相对指标 rd = OKLab 明度差 / 本主题正文(editor.foreground 于 editor.background)明度差 x 100; 绝对指标: apca = APCA Lc, de = OKLab ΔE x 100.
# 只处理主题自己定义了的键(没定义的由 VS Code 推导, 这里算不出推导值); 禁用状态不设下限; 与底色同色(ΔE < 1)的线条与层次底是原设计不画, 豁免.
# 配对的底色键按普查出现次数排序, 第一个最可靠; 其余可能是按颜色值反查来的同色键: 修复先求全部达标, 做不到只保证第一个, 门禁只判第一个.
# 前景键有同名底色键(xxx.activeForeground -> xxx.activeBackground)且主题定义了时, 它排第一: 普查按值反查可能认成同色的别的底色键(如 Ayu 的按钮底).
# 底色弱(层次底)只报告不修不门禁: 原主题常故意做平再靠边框区分(如 One Light 白输入框), 它又是字与选区的底, 改它会连锁带动别的颜色.
# 终端颜色(terminal.*)不在这里处理, 由 themes.py 的终端步骤与门禁负责.
# 只有字可以调到底色的另一侧(深底浅字 <-> 浅底深字); 线条与底色只往底色有余地的一侧调(浅底往暗, 深底往亮), 不反转原设计.
import json, math, os, re

from colorlib import Rgb, blend, from_oklch, h, hx, oklch

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'levels.json')
_DOC = None


def doc() -> dict:
    global _DOC
    if _DOC is None:
        _DOC = json.load(open(PATH, encoding='utf-8'))
    return _DOC


def parse(v) -> tuple[Rgb, float] | None:
    if not isinstance(v, str):
        return None
    m = re.fullmatch(r'#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?', v)
    if not m:
        return None
    return h(m.group(1)), int(m.group(2), 16) / 255 if m.group(2) else 1.0


def apca(txt: Rgb, bg: Rgb) -> float:
    """APCA-W3 0.0.98G-4g 的 |Lc|."""
    y = lambda c: 0.2126729 * c[0] ** 2.4 + 0.7151522 * c[1] ** 2.4 + 0.0721750 * c[2] ** 2.4
    clamp = lambda v: v if v > 0.022 else v + (0.022 - v) ** 1.414
    t, b = clamp(y(txt)), clamp(y(bg))
    if abs(b - t) < 0.0005:
        return 0.0
    if b > t:
        s = (b ** 0.56 - t ** 0.57) * 1.14
        out = 0 if s < 0.1 else s - 0.027
    else:
        s = (b ** 0.65 - t ** 0.62) * 1.14
        out = 0 if s > -0.1 else s + 0.027
    return abs(out) * 100


def _lab(c: Rgb) -> tuple[float, float, float]:
    L, C, H = oklch(c)
    return L, C * math.cos(H), C * math.sin(H)


def dl(a: Rgb, b: Rgb) -> float:
    return abs(oklch(a)[0] - oklch(b)[0]) * 100


def de(a: Rgb, b: Rgb) -> float:
    return math.dist(_lab(a), _lab(b)) * 100


def body_dl(colors: dict, t: dict) -> float:
    fg, bg = parse(colors.get('editor.foreground')), parse(colors.get('editor.background'))
    return max(1.0, dl(fg[0] if fg else t['fg'], bg[0] if bg else t['bg']))


def under(colors: dict, key: str, t: dict) -> Rgb:
    """底色键的实际颜色: 半透明的叠在编辑区底上; 主题没定义时按编辑区底近似."""
    p = parse(colors.get(key))
    if p is None:
        return t['bg']
    rgb, a = p
    return blend(rgb, t['bg'], a) if a < 1 else rgb


def exempt(key: str, level: str) -> str | None:
    if re.search('disabled', key, re.I):
        return '禁用'
    if level == '底色弱':
        return '层次底只报告'
    return None


def measure(c: Rgb, bg: Rgb, level: str, base: float) -> tuple[float, float]:
    lv = doc()['levels'][level]
    return dl(c, bg) / base * 100, (apca(c, bg) if lv['abs_metric'] == 'apca' else de(c, bg))


def short(c: Rgb, a: float, bgs: list[Rgb], level: str, base: float) -> bool:
    lv = doc()['levels'][level]
    for bg in bgs:
        fg = blend(c, bg, a) if a < 1 else c
        rd, ab = measure(fg, bg, level, base)
        if rd < lv['lo'] - 0.05 or ab < lv['abs'] - 0.05:
            return True
    return False


def targets(colors: dict, t: dict) -> list[tuple[str, str, list[str]]]:
    """要检查的 (键, 级, 底色键们): 主题定义了该键, 且有实测配对; 按 底色 -> 线条 -> 字 的顺序, 字按调整后的底色判断."""
    d = doc()
    order = {'底色': 0, '线条': 1, '内容': 2, '暗化': 2}
    out = []
    for k, unders in d['pairs'].items():
        lv = d['keyLevels'].get(k, '')
        if lv[:2] not in order or parse(colors.get(k)) is None or k.startswith('terminal.'):
            continue
        own = re.sub(r'(?i)foreground$', lambda m: 'Background' if m.group(0)[0] == 'F' else 'background', k)
        if own != k and parse(colors.get(own)) is not None:
            unders = [own] + [u for u in unders if u != own]
        out.append((k, lv, unders))
    return sorted(out, key=lambda x: (order[x[1][:2]], x[0]))


def same_color(c: Rgb, a: float, bgs: list[Rgb], key: str, level: str) -> bool:
    if not (level.startswith('线条') or level == '底色弱') or re.search(doc()['exemptSameColor'], key, re.I):
        return False
    return all(de(blend(c, bg, a) if a < 1 else c, bg) < 1 for bg in bgs)


def check(colors: dict, t: dict, all_unders: bool = False) -> list[str]:
    """越线项: '键(级) 于 底色键 rd x < 下限' 或 绝对指标不足; 豁免的不报. 默认只判第一个(最可靠的)底色键."""
    base, out = body_dl(colors, t), []
    for k, lv, unders in targets(colors, t):
        c, a = parse(colors[k])
        bgs = [under(colors, u, t) for u in unders]
        if exempt(k, lv) or same_color(c, a, bgs, k, lv):
            continue
        L = doc()['levels'][lv]
        for u, bg in list(zip(unders, bgs))[:None if all_unders else 1]:
            fg = blend(c, bg, a) if a < 1 else c
            rd, ab = measure(fg, bg, lv, base)
            if rd < L['lo'] - 0.05 or ab < L['abs'] - 0.05:
                out.append(f"{k}({lv}) 于 {u}: rd {rd:.1f} / {L['abs_metric']} {ab:.1f}, 下限 {L['lo']} / {L['abs']}")
    return out


def fix(colors: dict, t: dict) -> list[str]:
    """把低于修复下限 / 绝对下限的键提到刚好达标: 半透明的先加不透明度; 不够再只调 OKLCH 明度(远离底色), 色相与彩度不变(出色域时降彩度)."""
    base, log = body_dl(colors, t), []
    for k, lv, unders in targets(colors, t):
        c, a = parse(colors[k])
        bgs = [under(colors, u, t) for u in unders]
        if exempt(k, lv) or same_color(c, a, bgs, k, lv) or not short(c, a, bgs, lv, base):
            continue
        before = colors[k]
        while a < 1 and short(c, a, bgs, lv, base):
            a = min(1.0, a + 0.02)
        if not short(c, a, bgs, lv, base) and not short(c, round(a * 255) / 255, bgs, lv, base):
            colors[k] = hx(c) + ('%02X' % round(a * 255) if a < 1 else '')
            log.append(f'{k}({lv}) {before} -> {colors[k]} 加不透明度')
            continue
        L0, C0, H0 = oklch(c)
        # 往远离主要底色的方向调明度; 那一侧到头仍不够时换另一侧; 全部底色都做不到时只保证第一个
        main = oklch(bgs[0])[0]
        done = False
        for group in ([bgs, bgs[:1]] if len(bgs) > 1 else [bgs]):
            # 字: 先往远离底色的一侧, 到头不够再换另一侧; 线条与底色: 只往底色有余地的一侧(浅底往暗, 深底往亮), 与原值稍亮稍暗无关
            ends = ([1.0, 0.0] if L0 >= main else [0.0, 1.0]) if lv[:2] in ('内容', '暗化') else [0.0 if main >= 0.5 else 1.0]
            for end in ends:
                if short(from_oklch(end, C0, H0), 1.0, group, lv, base):
                    continue
                lo_, hi_ = L0, end
                for _ in range(30):
                    mid = (lo_ + hi_) / 2
                    lo_, hi_ = (mid, hi_) if short(from_oklch(mid, C0, H0), 1.0, group, lv, base) else (lo_, mid)
                # 写成 #RRGGBB 的取整可能又落回线下, 再往同一方向推一小步
                step = 0.002 if end > L0 else -0.002
                for _ in range(50):
                    if not short(h(hx(from_oklch(hi_, C0, H0))), 1.0, group, lv, base):
                        break
                    hi_ = min(1.0, max(0.0, hi_ + step))
                colors[k] = hx(from_oklch(hi_, C0, H0))
                log.append(f'{k}({lv}) {before} -> {colors[k]}' + ('' if group is bgs else ' (只保证主要底色)'))
                done = True
                break
            if done:
                break
        if not done:
            log.append(f'{k}({lv}) {before} 无法达标(明度到头仍不足), 未改')
    return log
