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


def tune(hexc: str, bg: Rgb, cap: float, min_cr: float, dl: float = 0.0) -> Rgb:
    """彩度封顶 cap, 明度偏移 dl, 再沿远离背景的方向推明度直到对比度 >= min_cr; 色相不变."""
    L, C, H = oklch(h(hexc))
    L += dl
    C = min(C, cap)
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
    while cr(c, bg) > max_cr + 0.004 and 0 < L < 1:
        L += step
        c = from_oklch(L, C, H)
    return c
