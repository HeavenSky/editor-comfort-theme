# /// script
# requires-python = ">=3.11"
# ///
# 生成符合门禁口径的完整 Claude Code 自定义主题(72 个颜色全部覆盖), 写到 ~/.claude/themes/.
# 配色来源二选一:
#   默认: 读当前终端的底色, 正文色与 16 色(OSC 11 / 10 / 4), 写 comfort-light.json 或 comfort-dark.json
#   传本项目主题名(如 moka-dark): 取 themes/<名字>.json 的 terminal.* 颜色, 写 comfort-<名字>.json; 不需要在终端里运行
# 每个颜色取哪个终端色, 属于哪一类, 沿用 tools/terminal/claude-theme.sh 里的对应表(单一来源).
# 与 shell 版按固定比例混色不同, 这里按 comfort.py 终端范围的口径(term_spec)在 OKLCH 里逐个求色:
#   text 正文: 终端正文色, 收回极端黑白; bg: 终端底色
#   gray 次要文字与边框: 按对比度目标取色(次要文字落在终端 90m 的区间, 其余自定), 带正文色的色相
#   accent 强调色: 终端色, 对比度不低于 4.5, 深色主题不比正文亮 1.2 倍以上, 去荧光感, 调明度时保持饱和度
#   tint 背景块(diff, 消息底, 选区): 对应色相的淡色, 荧光度, 与底色对比度, 正文压在上面的对比度, 亮色块饱和度都按口径
# 生成后按同一口径检查, 未达标时列出问题并以退出码 1 结束.
#
# 用法: uv run tools/check/claude_theme.py              按当前终端配色
#       uv run tools/check/claude_theme.py moka-dark    按本项目主题; 名字不存在时列出可用主题
# 启动: claude --settings '{"theme":"custom:comfort-dark"}'   (浅色为 comfort-light, 按主题生成的为 comfort-moka-dark 等)
import json, os, re, sys

sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', d) for d in ('lib', 'gen', 'check', 'lab')]
from colorlib import cr, deneon, fit, from_oklch, h, hx, lum, neon, oklch, sat, unextreme
from comfort import BRIGHT_TINT_L, BRIGHT_TINT_SAT, EXTREME_DARK, EXTREME_LIGHT, term_spec

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SHELL = os.path.join(ROOT, 'tools', 'terminal', 'claude-theme.sh')
THEMES = os.path.expanduser('~/.claude/themes')
PROJECT_THEMES = os.path.join(ROOT, 'themes')
NAMES = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
# 强调色与荧光度取门禁终端范围(comfort.term_spec)的理想值, 不借用编辑区 / 界面的口径; 荧光度与亮度上限深浅相同, 彩字下限浅色更高
_TS = term_spec(True)
NEON_LIMIT = _TS['neon'][1]
NEON_MAX, ACCENT_GLARE = NEON_LIMIT - 0.005, _TS['glare'][1]


def accent_min(light: bool) -> float:
    return term_spec(not light)['accent'][0]


# 背景块(diff, 消息底, 选区)门禁终端范围没有对应指标, 在这里自定: 与底色对比度上限, 压在上面的正文对比度下限
TINT_MAX_CR, TEXT_ON_MIN = 2.2, 4.5
# 亮的背景块饱和度: 与编辑区高亮底同一口径(comfort.BRIGHT_TINT_L / BRIGHT_TINT_SAT, 理想 <= 0.40, 超过 0.55 判不通过)
TINT_LIGHT_L, (TINT_SAT_MAX, TINT_SAT_LIMIT) = BRIGHT_TINT_L, BRIGHT_TINT_SAT
# 次要文字与边框的对比度目标: inactive 落在门禁终端 90m 的理想区间(3.4~4.2), 其余为本主题自定(终端范围无对应指标)
GRAY_CR = dict(inactive=3.8, inactiveShimmer=5.0, subtle=2.4, promptBorder=1.6, promptBorderShimmer=2.6, rate_limit_empty=1.8)
# 背景块: (相对底色的明度差, 彩度); 浅色主题往深, 深色主题往亮 x 1.8; 色相取对应终端色(fg 为正文色)
TINT = dict(userMessageBackground=(0.035, 0.012), userMessageBackgroundHover=(0.055, 0.014), composerSidebarBackground=(0.025, 0.010),
            memoryBackgroundColor=(0.035, 0.025), bashMessageBackgroundColor=(0.035, 0.025), selectionBg=(0.090, 0.050),
            diffAdded=(0.035, 0.050), diffAddedDimmed=(0.015, 0.025), diffAddedWord=(0.085, 0.080),
            diffRemoved=(0.035, 0.045), diffRemovedDimmed=(0.015, 0.022), diffRemovedWord=(0.085, 0.075))


def table() -> list[tuple]:
    """tools/terminal/claude-theme.sh 里的对应表: (颜色名, 浅色取的终端色, 深色取的终端色, 类型, 混入的颜色)."""
    s = open(SHELL, encoding='utf-8').read()
    body = s[s.index("table=$(cat <<'EOF'\n") + len("table=$(cat <<'EOF'\n"):s.index('\nEOF\n)')]
    return [tuple(line.split()[:5]) for line in body.splitlines() if line.strip()]


def query(codes: list[str]) -> dict:
    """向终端查询颜色(OSC 11 底色 / 10 正文 / 4;N 第 N 色), 返回 {编号: rgb}; 终端不回应的编号缺省."""
    import select, termios, tty
    try:
        fd = os.open('/dev/tty', os.O_RDWR)
    except OSError:
        return {}
    old = termios.tcgetattr(fd)
    out = {}
    try:
        tty.setraw(fd)
        for code in codes:
            os.write(fd, f'\033]{code};?\007'.encode())
            buf = b''
            while select.select([fd], [], [], 0.5)[0]:
                buf += os.read(fd, 64)
                if buf.endswith((b'\007', b'\033\\')):
                    break
            m = re.search(rb'rgb:([0-9a-fA-F]{2})[0-9a-fA-F]*/([0-9a-fA-F]{2})[0-9a-fA-F]*/([0-9a-fA-F]{2})', buf)
            if not m:
                break
            out[code] = h(b''.join(m.groups()).decode())
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        os.close(fd)
    return out


def from_theme(name: str) -> tuple[str, dict]:
    """本项目主题的终端配色, 返回 (主题短名, 与 query 同形的 {编号: rgb}); 找不到主题时抛 SystemExit 并列出可用名字."""
    short = name.removesuffix('.json')
    path = os.path.join(PROJECT_THEMES, f'{short}.json')
    if not os.path.isfile(path):
        names = sorted(f[:-len('.json')] for f in os.listdir(PROJECT_THEMES) if f.endswith('.json'))
        raise SystemExit(f'没有主题 {name}; 可用: {", ".join(names)}')
    colors = json.load(open(path, encoding='utf-8'))['colors']
    term = {'11': h(colors['terminal.background'][1:7]), '10': h(colors['terminal.foreground'][1:7])}
    for i, n in enumerate(NAMES * 2):
        key = f'terminal.ansi{"Bright" if i >= 8 else ""}{n.capitalize()}'
        term[f'4;{i}'] = h(colors[key][1:7])
    return short, term


def slot(name: str) -> str:
    base = name.removesuffix('Bright')
    return f'4;{NAMES.index(base) + (8 if base != name else 0)}'


def is_light(bg) -> bool:
    # 与 Claude Code 判断终端明暗的口径一致: 未线性化的 sRGB 按亮度系数加权, > 0.5 为浅色
    return 0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2] > 0.5


def build(term: dict) -> tuple[str, dict]:
    bg, fg = term['11'], unextreme(term['10'])
    light = is_light(bg)
    mode = 'light' if light else 'dark'
    text = cr(fg, bg)
    Lb = oklch(bg)[0]
    out = {}
    for token, lslot, dslot, kind, src in table():
        s = lslot if light else dslot
        if kind == 'text':
            c = fg
        elif kind == 'bg':
            c = bg
        elif kind == 'gray':
            # 带正文色的色相, 饱和度取正文色的(灰阶仍是灰), 对比度到目标
            target = min(GRAY_CR[token], text * 0.95)
            c = fit(fg, bg, lo=target, hi=target)
        elif kind == 'accent':
            c = term[slot(s)]
            c = fit(c, bg, lo=accent_min(light), hi=text * ACCENT_GLARE if not light else None)
            c = deneon(c, NEON_MAX, bg, accent_min(light))
        else:
            dl, C = TINT[token]
            hue = oklch(fg if src == 'fg' else term[slot(src)])[2]
            L = Lb - dl if light else Lb + dl * 1.8
            c = from_oklch(L, C, hue)
            while (neon(c) > NEON_MAX or cr(c, bg) > TINT_MAX_CR - 0.6
                   or (oklch(c)[0] > TINT_LIGHT_L and sat(c) > TINT_SAT_MAX - 0.02)) and C > 0.005:
                C *= 0.92
                c = from_oklch(L, C, hue)
            # 正文压在上面读不清时把底往底色方向挪回(留 0.03 余量防 hex 取整)
            while cr(fg, c) < TEXT_ON_MIN + 0.03 and abs(L - Lb) > 0.004:
                L += 0.004 if light else -0.004
                c = from_oklch(L, C, hue)
        out[token] = hx(unextreme(c))
    return mode, out


def check(bg, fg, colors: dict) -> list[str]:
    kinds = {t[0]: t[3] for t in table()}
    lo = accent_min(is_light(bg))
    bad = []
    for k, v in colors.items():
        c = h(v[1:])
        if neon(c) > NEON_LIMIT:
            bad.append(f'{k} 荧光度 {neon(c):.3f} > {NEON_LIMIT}')
        if not EXTREME_DARK <= lum(c) <= EXTREME_LIGHT:
            bad.append(f'{k} 亮度 {lum(c):.3f} 落在极端黑白')
        if kinds[k] == 'tint':
            if cr(c, bg) > TINT_MAX_CR:
                bad.append(f'{k} 与底色对比度 {cr(c, bg):.2f} > {TINT_MAX_CR}')
            if cr(fg, c) < TEXT_ON_MIN:
                bad.append(f'{k} 上的正文对比度 {cr(fg, c):.2f} < {TEXT_ON_MIN}')
            if oklch(c)[0] > TINT_LIGHT_L and sat(c) > TINT_SAT_LIMIT:
                bad.append(f'{k} 亮色块饱和度 {sat(c):.2f} > {TINT_SAT_LIMIT}')
        if kinds[k] == 'accent' and cr(c, bg) < lo - 0.05:
            bad.append(f'{k} 对比度 {cr(c, bg):.2f} < {lo}')
    return bad


def main() -> int:
    args = sys.argv[1:]
    if len(args) > 1 or (args and args[0].startswith('-')):
        print('用法: uv run tools/check/claude_theme.py [本项目主题名, 如 moka-dark]', file=sys.stderr)
        return 2
    if args:
        short, term = from_theme(args[0])
    else:
        short = None
        codes = ['11', '10'] + [f'4;{i}' for i in range(16)]
        term = query(codes)
        if len(term) < len(codes):
            print('终端没有回应颜色查询(OSC 11 / 10 / 4; 不支持, 或在 tmux / ssh 里); 可改传本项目主题名', file=sys.stderr)
            return 1
    mode, colors = build(term)
    name = f'comfort-{short or mode}'
    os.makedirs(THEMES, exist_ok=True)
    path = os.path.join(THEMES, name + '.json')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'name': name, 'base': mode, 'overrides': colors}, indent=2, ensure_ascii=False) + '\n')
    print(f'已写 {path}')
    print(f"启动: claude --settings '{{\"theme\":\"custom:{name}\"}}'")
    bad = check(term['11'], h(colors['text'][1:]), colors)
    if bad:
        print('未达门禁口径:', *bad, sep='\n  ', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
