# /// script
# requires-python = ">=3.11"
# dependencies = ["pyobjc-framework-Cocoa; sys_platform == 'darwin'"]
# ///
# 计算主题的 清晰 / 护眼 指标并评级, 以及 柔和安静 / 护眼防疲劳 两项打分(规则见 comfort.py);
# 支持 Terminal.app 的 .terminal 与 VS Code 颜色主题 .json.
# 用法: uv run tools/metrics.py [--check] [--strict] [--detail] <文件>...
#   --check: 任一受检主题未达标(清晰 >= 中高, 护眼 = 好)时退出码 1; themes.py 中 gate=False 的主题只报告不判定.
#   --strict: 同时要求 柔和 与 防疲劳 两项通过(没有子指标越过限值).
#   --detail: 逐主题列出 柔和 / 防疲劳 的子指标取值与得分.
import json, os, plistlib, re, sys

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import Rgb, blend, cr, h, lum, oklch
from comfort import NAMES, rate
from gen_vscode import REGISTRY as REGISTRY_PATH, UI_PAIRS

# VS Code 注册表里默认值硬编码的键; 主题不定义它们时界面落到与主题无关的颜色, 受检主题必须全部覆盖
REGISTRY = json.load(open(REGISTRY_PATH, encoding='utf-8'))['colors'] if os.path.exists(REGISTRY_PATH) else None

ANSI = ['Black', 'Red', 'Green', 'Yellow', 'Blue', 'Magenta', 'Cyan', 'White']

# 评级阈值; 改这里即改达标口径, 生成器的调色参数须同步满足
CLEAR_HIGH = dict(text=8.0, accent=5.0, badge=5.0)
CLEAR_HIGH_DARK_TEXT = (7.0, 8.5)  # 深色主题评"高"的正文区间: 再亮在暗底上发光, 与防疲劳规则一致
# 行号只需够读: 常驻视野边缘, 太亮抢眼; 当前行行号另有 activeForeground 保持明亮
CLEAR_MID_HIGH = dict(text=6.0, accent=4.5, badge=4.0, comment=3.0, ui=4.5, line_no=2.0)
EYE_MAX_CHROMA = 0.14
COMMENT_MAX = 4.2           # 注释对比度上限: 再亮会和正文抢注意力(注释随正文联动, 目标 正文 / 1.85)
SYNTAX_MAX_RATIO = 1.1      # 深色主题语法色对比度上限 = 正文 x 该值: 再亮会比正文更抢眼
EYE_DARK_MIN_BG = 0.01      # 深色底亮度下限: 低于它接近纯黑
EYE_LIGHT_MAX_BG = 0.90     # 浅色底亮度上限: 高于它接近纯白, 眩光大


def _ansi_stats(pal: list[Rgb], bg: Rgb) -> dict:
    col, bcol = pal[1:7], pal[9:15]
    return dict(
        accent=min(cr(c, bg) for c in col),
        bright=min(cr(c, bg) for c in bcol),
        badge=min(max(cr(pal[0], c), cr(pal[15], c), cr(pal[7], c)) for c in col + bcol),
        comment=cr(pal[8], bg),
        chroma=[oklch(c)[1] for c in col + bcol],
    )


def from_terminal(path: str) -> dict:
    from AppKit import NSColorSpace, NSKeyedUnarchiver

    def rgb(d: bytes) -> Rgb:
        c = NSKeyedUnarchiver.unarchiveObjectWithData_(d).colorUsingColorSpace_(NSColorSpace.sRGBColorSpace())
        return (c.redComponent(), c.greenComponent(), c.blueComponent())

    p = plistlib.load(open(path, 'rb'))
    bg, fg = rgb(p['BackgroundColor']), rgb(p['TextColor'])
    pal = [rgb(p[f'ANSI{n}Color']) for n in ANSI] + [rgb(p[f'ANSIBright{n}Color']) for n in ANSI]
    st = _ansi_stats(pal, bg)
    return dict(kind='terminal', bg=bg, fg=fg, text=cr(fg, bg), **st)


def _parse(v: str, under: Rgb) -> Rgb:
    v = v.lstrip('#')
    if len(v) in (3, 4):
        v = ''.join(ch * 2 for ch in v)
    c = h(v[:6])
    return blend(c, under, int(v[6:8], 16) / 255) if len(v) == 8 else c


def from_vscode(path: str) -> dict:
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    t = json.loads(s)
    c = t['colors']
    bg = _parse(c['editor.background'], h('#000000'))
    col = lambda k, under=bg: _parse(c[k], under) if k in c else None
    fg = col('editor.foreground')
    syn, comment, comment_main = [], None, None
    for r in t.get('tokenColors', []):
        f = r.get('settings', {}).get('foreground')
        if not f:
            continue
        rgb = _parse(f, bg)
        scopes = r.get('scope') or []
        scopes = scopes if isinstance(scopes, list) else [scopes]
        # 与 gen_vscode 同口径: 作用域里出现 comment 的规则(含 punctuation.definition.comment)都按注释计
        if any('comment' in str(x) for x in scopes):
            comment = rgb if comment is None or cr(rgb, bg) < cr(comment, bg) else comment
            if 'comment' in (x.strip() for sc in scopes for x in str(sc).split(',')):
                comment_main = rgb
        elif not any(str(x).startswith(('invalid', 'markup.inserted', 'markup.deleted')) for x in scopes):
            syn.append(rgb)
    # 括号对着色画在代码上, 与语法色同等对待; 主题不定义时 VS Code 用高饱和默认色, 按默认值计入
    for k, default in (('editorBracketHighlight.foreground1', '#FFD700'), ('editorBracketHighlight.foreground2', '#DA70D6'),
                       ('editorBracketHighlight.foreground3', '#179FFF')):
        syn.append(_parse(c.get(k, default), bg))
    for v in (t.get('semanticTokenColors') or {}).values():
        f = v if isinstance(v, str) else v.get('foreground')
        if f:
            syn.append(_parse(f, bg))
    ui = [cr(col(a, col(b) or bg), col(b) or bg) for a, b, need in UI_PAIRS if need >= 4.5 and a in c]
    mode = 'dark' if t.get('type') == 'dark' else 'light'
    uncovered = sorted(k for k, v in REGISTRY.items() if v.get(mode) and k not in c) if REGISTRY else None
    pal = [col(f'terminal.ansi{n}') for n in ANSI] + [col(f'terminal.ansiBright{n}') for n in ANSI]
    out = dict(kind='vscode', bg=bg, fg=fg, colors=c, syn_colors=syn, text=cr(fg, bg), syntax=min(cr(x, bg) for x in syn), syntax_top=max(cr(x, bg) for x in syn),
               syn_chroma=[oklch(x)[1] for x in syn], comment=cr(comment, bg) if comment else None,
               comment_main=cr(comment_main, bg) if comment_main else None,
               line_no=cr(col('editorLineNumber.foreground'), bg) if 'editorLineNumber.foreground' in c else None,
               ui=min(ui) if ui else None, dark=t.get('type') == 'dark', uncovered=uncovered)
    if all(pal):
        st = _ansi_stats(pal, col('terminal.background') or bg)
        out.update(term_accent=st['accent'], badge=st['badge'], chroma=st['chroma'] + out['syn_chroma'])
    else:
        out.update(term_accent=None, badge=None, chroma=out['syn_chroma'])
    return out


def grade(m: dict) -> tuple[str, str, list[str]]:
    # 按表格显示精度判定: 颜色经 hex 量化后常落在 4.49 / 0.1401 这类边界上, 不取整会出现显示达标却判失败
    m = {k: (round(v, 1) if k in ('text', 'syntax', 'comment', 'line_no', 'ui', 'term_accent', 'badge', 'accent', 'bright')
             and v is not None else v) for k, v in m.items()}
    m['chroma'] = [round(x, 3) for x in m['chroma']]
    why = []
    if m['kind'] == 'terminal':
        acc, badge, extra = m['accent'], m['badge'], {'comment': m['comment']}
    else:
        acc = min(x for x in (m['syntax'], m['term_accent']) if x is not None)
        badge = m['badge'] if m['badge'] is not None else 99
        extra = {'comment': m['comment'], 'ui': m['ui'], 'line_no': m['line_no']}
    lo, hi = CLEAR_HIGH_DARK_TEXT if lum(m['bg']) < 0.2 else (CLEAR_HIGH['text'], 99)
    if lo <= m['text'] <= hi and acc >= CLEAR_HIGH['accent'] and badge >= CLEAR_HIGH['badge'] and \
            all(v is None or v >= CLEAR_MID_HIGH[k] for k, v in extra.items()):
        clear = '高'
    else:
        checks = dict(text=m['text'], accent=acc, badge=badge, **extra)
        for k, v in checks.items():
            if v is not None and v < CLEAR_MID_HIGH[k]:
                why.append(f'{k} {v:.1f} < {CLEAR_MID_HIGH[k]}')
        clear = '中高' if not why else '中'
    dark = lum(m['bg']) < 0.2
    if m['kind'] == 'vscode':
        if m['comment'] is not None and m['comment'] > COMMENT_MAX:
            why.append(f"注释 {m['comment']:.1f} > {COMMENT_MAX}")
        if dark and round(m['syntax_top'], 1) > round(m['text'] * SYNTAX_MAX_RATIO, 1):
            why.append(f"最亮语法色 {m['syntax_top']:.1f} > 正文 x {SYNTAX_MAX_RATIO} = {m['text'] * SYNTAX_MAX_RATIO:.1f}")
        if why and clear != '中':
            clear = '中'
    eye_why = []
    if max(m['chroma']) > EYE_MAX_CHROMA:
        eye_why.append(f"最大彩度 {max(m['chroma']):.3f} > {EYE_MAX_CHROMA}")
    if dark and lum(m['bg']) < EYE_DARK_MIN_BG:
        eye_why.append(f"底亮度 {lum(m['bg']):.3f} < {EYE_DARK_MIN_BG}(近纯黑)")
    if not dark and lum(m['bg']) > EYE_LIGHT_MAX_BG:
        eye_why.append(f"底亮度 {lum(m['bg']):.3f} > {EYE_LIGHT_MAX_BG}(近纯白)")
    return clear, ('好' if not eye_why else '中'), why + eye_why


def exempt_names() -> set[str]:
    try:
        from themes import build
        return {t['name'] for t in build() if not t['gate']}
    except Exception:
        return set()


def fmt(v) -> str:
    return '  -  ' if v is None else f'{v:5.1f}'


def main() -> int:
    check, strict, detail = '--check' in sys.argv, '--strict' in sys.argv, '--detail' in sys.argv
    files = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not files:
        print(__doc__ or '用法: uv run tools/metrics.py [--check] <文件>...')
        return 2
    exempt, failed = exempt_names(), []
    rows_t, rows_v = [], []
    for f in files:
        name = re.sub(r'(-color-theme)?\.(terminal|json)$', '', os.path.basename(f))
        m = from_terminal(f) if f.endswith('.terminal') else from_vscode(f)
        clear, eye, why = grade(m)
        r = rate(m)
        m['soft'], m['fatigue'] = r['soft'], r['fatigue']
        gated = name not in exempt
        if m.get('uncovered'):
            why.append(f"未覆盖 VS Code 硬编码默认色的键 {len(m['uncovered'])} 个, 例: {', '.join(m['uncovered'][:4])}")
        ok = clear in ('高', '中高') and eye == '好' and not m.get('uncovered')
        if strict:
            for key, label in (('soft', '柔和'), ('fatigue', '防疲劳')):
                if not r[key]['ok']:
                    ok = False
                    why.extend(f'{label}: {w}' for w in r[key]['why'])
        if check and gated and not ok:
            failed.append((f, why))
        tag = '' if gated else ' (参考, 不门禁)'
        (rows_t if m['kind'] == 'terminal' else rows_v).append((name, m, clear, eye, tag))
    score = lambda r: f"{r['score']:>3}{' ' if r['ok'] else '×'}"
    if rows_t:
        print('Terminal       主题               正文  彩字  亮色  徽标   90m | 底亮度 最大彩度 | 清晰 护眼 | 柔和 防疲劳')
        for name, m, clear, eye, tag in rows_t:
            print(f"  {name:28} {fmt(m['text'])} {fmt(m['accent'])} {fmt(m['bright'])} {fmt(m['badge'])} {fmt(m['comment'])} |"
                  f" {lum(m['bg']):.3f}  {max(m['chroma']):.3f}  | {clear:3} {eye}  | {score(m['soft'])}  {score(m['fatigue'])}{tag}")
    if rows_v:
        print('VS Code        主题               正文  语法  注释  行号  界面  终端  徽标 | 底亮度 最大彩度 | 未覆盖 | 清晰 护眼 | 柔和 防疲劳')
        for name, m, clear, eye, tag in rows_v:
            print(f"  {name:28} {fmt(m['text'])} {fmt(m['syntax'])} {fmt(m['comment'])} {fmt(m['line_no'])} {fmt(m['ui'])}"
                  f" {fmt(m['term_accent'])} {fmt(m['badge'])} | {lum(m['bg']):.3f}  {max(m['chroma']):.3f}  |"
                  f" {'-' if m['uncovered'] is None else len(m['uncovered']):>5}  | {clear:3} {eye}  | {score(m['soft'])}  {score(m['fatigue'])}{tag}")
    if detail:
        print('\n子指标(取值 得分; × 为越过限值):')
        for name, m, *_ in rows_t + rows_v:
            for key, label in (('soft', '柔和'), ('fatigue', '防疲劳')):
                parts = [f"{NAMES[k]} {v:.3g} {s:.0f}{'' if s >= 60 else '×'}" for k, (v, s) in m[key]['subs'].items()]
                print(f"  {name:26} {label:4} {m[key]['score']:>3}: " + ' | '.join(parts))
    if failed:
        print('\n未达标(清晰 >= 中高, 护眼 = 好' + (', 柔和与防疲劳通过' if strict else '') + '):')
        for f, why in failed:
            print(f'  {f}: ' + '; '.join(why))
        return 1
    if check:
        print('\n全部受检主题达标')
    return 0


if __name__ == '__main__':
    sys.exit(main())
