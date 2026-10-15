# 颜色计算: sRGB 与 OKLCH 互转, WCAG 对比度, 以及按 彩度上限 + 对比度下限 调色.
import math

Rgb = tuple[float, float, float]


def h(s: str) -> Rgb:
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))


def hx(c: Rgb) -> str:
    return '#%02X%02X%02X' % tuple(round(min(1, max(0, v)) * 255) for v in c)


def _lin(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _gam(v: float) -> float:
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def lum(c: Rgb) -> float:
    r, g, b = map(_lin, c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def cr(a: Rgb, b: Rgb) -> float:
    x, y = sorted([lum(a), lum(b)])
    return (y + 0.05) / (x + 0.05)


def oklch(c: Rgb) -> tuple[float, float, float]:
    r, g, b = map(_lin, c)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(A, B), math.atan2(B, A)


def _rgb(L: float, C: float, H: float) -> Rgb:
    A, B = C * math.cos(H), C * math.sin(H)
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def from_oklch(L: float, C: float, H: float) -> Rgb:
    # 出色域时降彩度而不是裁剪通道, 否则色相会偏
    ok = lambda c: all(-1e-7 <= v <= 1 + 1e-7 for v in _rgb(L, c, H))
    if not ok(C):
        lo, hi = 0.0, C
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if ok(mid) else (lo, mid)
        C = lo
    return tuple(_gam(min(1, max(0, v))) for v in _rgb(L, C, H))


def gamut_chroma(L: float, H: float) -> float:
    """同明度同色相下 sRGB 可达的最大彩度; 彩度除以它得相对彩度(饱和度), 不同色相可比."""
    lo, hi = 0.0, 0.4
    for _ in range(25):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if all(-1e-6 <= v <= 1 + 1e-6 for v in _rgb(L, mid, H)) else (lo, mid)
    return lo


def sat(c: Rgb) -> float:
    """相对彩度(饱和度) 0~1: 彩度 / 同明度同色相 sRGB 可达最大彩度."""
    L, C, H = oklch(c)
    g = gamut_chroma(L, H)
    return min(1.0, C / g) if g > 1e-6 else 0.0


def with_sat(L: float, s: float, H: float) -> Rgb:
    """按饱和度取色: 明度 L, 色相 H, 彩度 = s x 该明度色相下的可达最大彩度."""
    return from_oklch(L, s * gamut_chroma(L, H) * 0.999, H)


def blue_light(c: Rgb) -> float:
    """线性蓝通道发光量, 纯白 = 1; 蓝光危害集中在 415~455nm, sRGB 显示器里基本由蓝原色发出."""
    return _lin(c[2])


def soften(s: float, knee: float, floor: float = 0.0, k: float = 0.4) -> float:
    """饱和度平滑压缩: knee 以下原样, 超出部分只保留 k 倍(原来更艳的仍然更艳, 不削成同一个值); 结果不低于 floor."""
    return max(floor, s if s <= knee else knee + (s - knee) * k)


def fit(c: Rgb, bg: Rgb, lo: float | None = None, hi: float | None = None, s: float | None = None) -> Rgb:
    """沿明度把 c 与 bg 的对比度调进 [lo, hi], 色相不变, 饱和度保持 s(默认取 c 自身的饱和度).
    与 tune / toward_bg 的区别: 明度变了彩度跟着色域变, 压暗黄色或提亮蓝色时不会顺带变灰."""
    L, C, H = oklch(c)
    s = sat(c) if s is None else s
    out = with_sat(L, s, H)
    away = 0.002 if lum(bg) < 0.2 else -0.002  # 拉大对比度的方向
    while lo is not None and cr(out, bg) < lo and 0 < L + away < 1:
        L += away
        out = with_sat(L, s, H)
    while hi is not None and cr(out, bg) > hi + 0.004 and 0 < L - away < 1:
        L -= away
        out = with_sat(L, s, H)
    return out


def amber(H: float, L: float, dark: bool) -> float:
    """浅色主题里压深的黄色(OKLCH 色相 80°~115°)朝琥珀转一点(最多 12°): 低明度的正黄在 sRGB 里只剩橄榄 / 土黄, 琥珀仍然鲜明.
    深色主题与其他色相原样返回. H 为弧度."""
    deg = math.degrees(H) % 360
    if dark or not 80 <= deg <= 115 or L > 0.75:
        return H
    return math.radians(deg - min(12, (deg - 75) * 0.6))


# 荧光感: 黄绿到青(OKLCH 色相 95°~200°)是人眼最敏感的一段, 高明度时彩度又让它显得比实际亮度更亮(Helmholtz-Kohlrausch 效应),
# 像荧光笔. 荧光度 = 彩度 x (明度 - 0.6) / 0.4, 明度 0.6 以下不计; 如 Claude Code 浅色 diff 底 #69DB7C 为 0.084
NEON_HUE = (95, 200)


def neon(c: Rgb) -> float:
    L, C, H = oklch(c)
    deg = math.degrees(H) % 360
    if not NEON_HUE[0] <= deg <= NEON_HUE[1] or L <= 0.6:
        return 0.0
    return C * (L - 0.6) / 0.4


def deneon(c: Rgb, target: float, bg: Rgb | None = None, min_cr: float | None = None) -> Rgb:
    """荧光度降到 target 以内: 先降明度(深色底上不低于 min_cr), 不够再降彩度; 色相不变."""
    L, C, H = oklch(c)
    out = c
    while neon(out) > target and C > 0.01:
        n = from_oklch(L - 0.004, C, H)
        if bg is not None and min_cr is not None and cr(n, bg) < min_cr:
            C *= 0.97
            n = from_oklch(L, C, H)
        else:
            L -= 0.004
        out = n
    return out


WHITE_L, WHITE_C, WHITE_CAP = 0.95, 0.04, 0.88


def unwhite(c: Rgb) -> Rgb:
    """近纯白(OKLCH 明度 >= 0.95 且彩度 <= 0.04, 如 #FFFFFF / #F8F8F2 / #EEFFFF)压到明度 0.88(约 VS Code 深色默认正文 #D4D4D4), 色相与彩度不变; 其他颜色原样返回."""
    L, C, H = oklch(c)
    return from_oklch(WHITE_CAP, C, H) if L >= WHITE_L and C <= WHITE_C else c


def unextreme(c: Rgb, lo: float = 0.0085, hi: float = 0.875) -> Rgb:
    """把纯黑 / 乌黑, 纯白 / 亮白收回到亮度 [lo, hi] 之内, 色相与饱和度不变."""
    if lo <= lum(c) <= hi:
        return c
    L, C, H = oklch(c)
    s = sat(c)
    step = 0.002 if lum(c) < lo else -0.002
    out = c
    while not lo <= lum(out) <= hi and 0 < L + step < 1:
        L += step
        out = with_sat(L, s, H)
    return out


def tune(hexc: str, bg: Rgb, cap: float, min_cr: float, dl: float = 0.0) -> Rgb:
    """彩度封顶 cap, 明度偏移 dl, 再沿远离背景的方向推明度直到对比度 >= min_cr; 色相不变."""
    L, C, H = oklch(h(hexc))
    L += dl
    # 留 0.0015 余量, 避免 hex 取整后彩度越过 cap
    C = min(C, cap - 0.0015)
    c = from_oklch(L, C, H)
    step = 0.002 if lum(bg) < 0.2 else -0.002
    while cr(c, bg) < min_cr and 0 < L < 1:
        L += step
        c = from_oklch(L, C, H)
    return c


def shift(c: Rgb, dl: float) -> Rgb:
    L, C, H = oklch(c)
    return from_oklch(L + dl, C, H)


def blend(fg: Rgb, bg: Rgb, a: float) -> Rgb:
    return tuple(a * x + (1 - a) * y for x, y in zip(fg, bg))


def toward_bg(c: Rgb, bg: Rgb, max_cr: float) -> Rgb:
    """沿靠近背景的方向调明度, 直到对比度 <= max_cr; 色相与彩度不变."""
    L, C, H = oklch(c)
    step = -0.002 if lum(bg) < 0.2 else 0.002
    # 纯黑 / 纯白的 L 恰为 0 / 1, 不先挪进区间循环一步也不走
    L = min(max(L, 0.001), 0.999)
    while cr(c, bg) > max_cr + 0.004 and 0 < L < 1:
        L += step
        c = from_oklch(L, C, H)
    return c


def lab(c: Rgb) -> tuple[float, float, float]:
    """sRGB -> CIELAB(D65)."""
    r, g, b = map(_lin, c)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def de2000(a: Rgb, b: Rgb) -> float:
    """CIEDE2000 色差: < 1 基本不可察觉, 1~2 仔细对比可察觉, 2~10 一眼可见, > 10 明显不同."""
    L1, a1, b1 = lab(a)
    L2, a2, b2 = lab(b)
    C7 = ((math.hypot(a1, b1) + math.hypot(a2, b2)) / 2) ** 7
    G = 0.5 * (1 - math.sqrt(C7 / (C7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2p - h1p if abs(h2p - h1p) <= 180 else h2p - h1p - 360 if h2p > h1p else h2p - h1p + 360)
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    else:
        hbp = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Cb7 = Cbp ** 7
    Rt = -2 * math.sqrt(Cb7 / (Cb7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-(((hbp - 275) / 25) ** 2))))
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))
