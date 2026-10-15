# /// script
# requires-python = ">=3.11"
# dependencies = ["pyobjc-framework-Cocoa; sys_platform == 'darwin'"]
# ///
# 主题门禁打分: 范围(终端 / 编辑区 / 界面) x 维度(清晰 / 鲜艳柔和 / 防疲劳 / 护眼 / 防蓝光), 综合分按 终端 2 : 编辑区 2 : 界面 1 加权(规则见 comfort.py);
# 支持 Terminal.app 的 .terminal(只有终端范围)与 VS Code 颜色主题 .json.
# 用法: uv run tools/metrics.py [--check] [--detail] <文件>...
#   --check: 门禁只看清晰维度里有对应看不清类调色步骤(tools/steps.py)的子指标, 口径取该步骤的目标(CLEAR_GATE), 任一受检主题越过时退出码 1;
#            VS Code 主题另须符合 vscode://schemas/color-theme. 其余维度, 串色, 角色 / 终端色差, 硬编码默认色覆盖与常用 scope 着色只作报告
#            (第一目标是还原原主题, 原主题本来如此的不判不达标). themes.py 中 gate=False 的主题只报告不判定. --strict 为旧参数, 与 --check 相同.
#   --detail: 逐主题列出 15 格(维度 x 范围)的子指标取值与得分, 以及诊断: 语法色同彩度 / 同对比度占比(压平),
#             与原主题相比的色相偏移和饱和度损失(保真度, 仅本仓库主题).
import json, os, plistlib, re, sys

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import Rgb, blend, cr, h, lum, oklch, sat
from comfort import DIM_NAMES, DIMS, MAIN_ROLES, NAMES, SCOPE_NAMES, SCOPES, rate
from schema import HEX, problems as schema_problems
from coverage import missing as coverage_missing
from gen_vscode import REGISTRY as REGISTRY_PATH, UI_PAIRS, is_comment_rule

# VS Code 注册表里默认值硬编码的键; 主题不定义它们时界面落到与主题无关的颜色, 受检主题必须全部覆盖
REGISTRY = json.load(open(REGISTRY_PATH, encoding='utf-8'))['colors'] if os.path.exists(REGISTRY_PATH) else None

ANSI = ['Black', 'Red', 'Green', 'Yellow', 'Blue', 'Magenta', 'Cyan', 'White']


def _ansi_stats(pal: list[Rgb], bg: Rgb) -> dict:
    col, bcol = pal[1:7], pal[9:15]
    return dict(
        accent=min(cr(c, bg) for c in col),
        bright=min(cr(c, bg) for c in bcol),
        # 彩色底只看配黑字或白字的较好者: 默认文字色配彩色底(只写 41m)在任何调色板下都看不清, 计入会让每套主题都不达标
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
    sel = rgb(p['SelectionColor']) if 'SelectionColor' in p else None
    return dict(kind='terminal', bg=bg, fg=fg, text=cr(fg, bg), pal=pal, term_bg=bg, term_fg=fg, term_sel=sel, **st)


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
    # 按 VS Code 的实际读法: 未注册, 已废弃或格式不合法的颜色键不生效, 不参与计算; 违反 schema 之处另行计入门禁
    schema = schema_problems(t) if REGISTRY else []
    c = {k: v for k, v in t['colors'].items()
         if REGISTRY is None or (k in REGISTRY and not REGISTRY[k].get('deprecated') and isinstance(v, str) and HEX.match(v))}
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
        # 与 gen_vscode 同口径(is_comment_rule): 补全段的规则看角色, 原主题的规则按选择器里出现 comment 计
        if is_comment_rule(r):
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
    uncovered = sorted(k for k, v in REGISTRY.items() if v.get(mode) and not v.get('deprecated') and k not in c) if REGISTRY else None
    pal = [col(f'terminal.ansi{n}') for n in ANSI] + [col(f'terminal.ansiBright{n}') for n in ANSI]
    out = dict(kind='vscode', bg=bg, fg=fg, colors=c, rules=t.get('tokenColors', []), syn_colors=syn, text=cr(fg, bg), syntax=min(cr(x, bg) for x in syn), syntax_top=max(cr(x, bg) for x in syn),
               syn_chroma=[oklch(x)[1] for x in syn], comment=cr(comment, bg) if comment else None,
               comment_main=cr(comment_main, bg) if comment_main else None,
               line_no=cr(col('editorLineNumber.foreground'), bg) if 'editorLineNumber.foreground' in c else None,
               ui=min(ui) if ui else None, dark=t.get('type') == 'dark', uncovered=uncovered, schema=schema,
               scopes=coverage_missing(t.get('tokenColors', [])))
    if all(pal):
        tbg = col('terminal.background') or bg
        st = _ansi_stats(pal, tbg)
        # 选区按 VS Code 的缺省链: terminal.selectionBackground 缺省取 editor.selectionBackground,
        # 失焦选区缺省为选区的一半透明度
        raw = c.get('terminal.selectionBackground') or c.get('editor.selectionBackground')
        sel = _parse(raw, tbg) if raw else None
        if 'terminal.inactiveSelectionBackground' in c:
            sel_in = col('terminal.inactiveSelectionBackground', tbg)
        elif raw:
            v = raw.lstrip('#')
            sel_in = blend(h(v[:6]), tbg, (int(v[6:8], 16) / 255 if len(v) == 8 else 1.0) * 0.5)
        else:
            sel_in = None
        out.update(term_accent=st['accent'], badge=st['badge'], chroma=st['chroma'] + out['syn_chroma'],
                   pal=pal, term_bg=tbg, term_fg=col('terminal.foreground', tbg) or fg, term_sel=sel, term_sel_inactive=sel_in)
    else:
        out.update(term_accent=None, badge=None, chroma=out['syn_chroma'])
    return out



def exempt_names() -> set[str]:
    try:
        from themes import build
        return {t['name'] for t in build() if not t['gate']}
    except Exception:
        return set()


# 诊断阈值: 语法色同彩度 / 同对比度的占比超过它即判"压平"; 主要角色相对原主题色相偏移 / 饱和度保留比例的警告线
FLAT_SHARE, HUE_SHIFT_WARN, SAT_KEEP_WARN = 0.40, 15, 0.60


def fidelity(name: str, path: str) -> list[str]:
    """本仓库主题: 主要语法角色 结果色 vs 原主题色 的色相偏移与饱和度保留比例, 越过警告线的列出."""
    import math, pool
    from gen_vscode import load, source_fg
    from themes import build
    t = next((x for x in build() if x['name'] == name), None)
    if t is None:
        return []
    src, cur = load(os.path.join(pool.SOURCES, t['source'])), load(path)
    sfg, cfg = source_fg(src, t['dark']), cur['colors']['editor.foreground']
    out = []
    for r in MAIN_ROLES:
        a = pool._rgb(pool.role_value(src.get('tokenColors', []), r, sfg))
        b = pool._rgb(pool.role_value(cur.get('tokenColors', []), r, cfg))
        if not a or not b or oklch(a)[1] < 0.035:
            continue
        dh = abs((math.degrees(oklch(b)[2] - oklch(a)[2]) + 180) % 360 - 180)
        keep = sat(b) / sat(a) if sat(a) > 0 else 1
        if dh > HUE_SHIFT_WARN or keep < SAT_KEEP_WARN:
            out.append(f'{pool.NAMES.get(r, r)} 色相偏 {dh:.0f}° 饱和度保留 {keep:.0%}')
    return out


# 门禁: 范围 -> 子指标 -> 下限, 与 steps.py 看不清类步骤的目标一致(步骤名见注释); 生成时按目标求色, 取整与混色误差留 CLEAR_TOL.
# 选区类取门禁限值而非理想值: 正文本身偏淡时(如 Sunlit)选区与选区上的字兼顾不了, 步骤退而取 字可读(3.5)前提下最看得出的一档.
CLEAR_GATE = dict(
    term=dict(text=4.5, accent=4.5, bright=4.5, gray=3.4,                                   # text_floor, term_floor, term_gray_floor
              selection=1.2, inactive_selection=1.08, on_selection=3.5),                    # term_selection
    editor=dict(text=4.5, syntax=4.5, comment=3.4, line_no=2.2, on_highlight=3.5,           # text_floor, syntax_floor, comment_floor, ui_text_floor, highlight_text
                selection_visible=1.15),                                                    # selections
    ui=dict(ui_text=4.5, small_text=4.5, focus=3.0, input_selection=1.15, input_selection_text=3.5),  # ui_text_floor, badge / button / control_text, focus_floor, selections
)
CLEAR_TOL = 0.06


def clear_gate(r: dict) -> list[str]:
    """清晰门禁越线项: '范围/子指标 取值 < 下限'."""
    out = []
    for scope, subs in CLEAR_GATE.items():
        cell = r['cells'].get(('clear', scope))
        for k, lo in subs.items():
            v = cell['subs'].get(k, (None,))[0] if cell else None
            if v is not None and v < lo - CLEAR_TOL:
                out.append(f'{SCOPE_NAMES[scope]}/{NAMES[k]} {v:.3g} < {lo}')
    return out


def main() -> int:
    check = '--check' in sys.argv or '--strict' in sys.argv
    detail = '--detail' in sys.argv
    files = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not files:
        print(__doc__ or '用法: uv run tools/metrics.py [--check] [--detail] <文件>...')
        return 2
    exempt, failed, rows = exempt_names(), [], []
    for f in files:
        name = re.sub(r'(-color-theme)?\.(terminal|json)$', '', os.path.basename(f))
        m = from_terminal(f) if f.endswith('.terminal') else from_vscode(f)
        r = rate(m)
        why = [f"{DIM_NAMES[d]}/{SCOPE_NAMES[s]}: {w}" for (d, s), c in r['cells'].items() for w in c['why']]
        for (scope, kind), label in ((('ui', 'panel_glare'), '面板亮块'), (('ui', 'border'), '边框抢眼'), (('ui', 'control'), '控件抢眼'),
                                     (('ui', 'ui_glare'), '界面文字刺眼'), (('ui', 'gray_patch'), '灰块'), (('ui', 'bright_panel'), '浅色亮底'),
                                     (('ui', 'blue_panel'), '饱和蓝底'), (('ui', 'extreme'), '界面极端黑白'), (('editor', 'extreme'), '编辑区极端黑白')):
            keys = r['issues'].get(scope, {}).get(kind)
            if keys:
                why.append(f"{label}: {', '.join(keys[:6])}{' 等' if len(keys) > 6 else ''}")
        if m.get('uncovered'):
            why.append(f"未覆盖 VS Code 硬编码默认色的键 {len(m['uncovered'])} 个, 例: {', '.join(m['uncovered'][:4])}")
        if m.get('schema'):
            why.append(f"不符合 vscode://schemas/color-theme {len(m['schema'])} 处, 例: {'; '.join(m['schema'][:3])}")
        if m.get('scopes'):
            why.append(f"常用 scope 未着色 {len(m['scopes'])} 个: {', '.join(m['scopes'])}")
        gate = clear_gate(r) + ([f"不符合 vscode://schemas/color-theme {len(m['schema'])} 处, 例: {'; '.join(m['schema'][:3])}"] if m.get('schema') else [])
        gated = name not in exempt
        if check and gated and gate:
            failed.append((f, gate))
        rows.append((name, f, m, r, '' if gated else ' (参考, 不门禁)'))
    sc = lambda x: '  - ' if not x or x['score'] is None else f"{x['score']:>3}{' ' if x['ok'] else '×'}"
    dims = ' '.join(f'{DIM_NAMES[d][:2]:>4}' for d in DIMS)
    for kind, title in (('terminal', 'Terminal'), ('vscode', 'VS Code')):
        sel = [x for x in rows if x[2]['kind'] == kind]
        if not sel:
            continue
        extra = '' if kind == 'terminal' else ' 未覆盖 规范 着色 |'
        print(f"{title:14} {'主题':18} 正文 |{extra} 终端 编辑区 界面 | {dims} | 综合")
        for name, f, m, r, tag in sel:
            hard = '' if kind == 'terminal' else f" {len(m['uncovered'] or []):>5} {len(m['schema']):>4} {len(m['scopes']):>4} |"
            print(f"  {name:28} {m['text']:4.1f} |{hard} {sc(r['scope'].get('term'))} {sc(r['scope'].get('editor'))}  {sc(r['scope'].get('ui'))} |"
                  f" {' '.join(sc(r['dim'][d]) for d in DIMS)} | {sc(r['overall'])}{tag}")
    if detail:
        print('\n子指标(取值 得分; × 为越过限值):')
        for name, f, m, r, _ in rows:
            print(f'  {name}')
            for s in SCOPES:
                for d in DIMS:
                    c = r['cells'].get((d, s))
                    if not c:
                        continue
                    parts = [f"{NAMES[k]} {v:.3g} {x:.0f}{'' if x >= 60 else '×'}" for k, (v, x) in c['subs'].items()]
                    print(f"    {SCOPE_NAMES[s]:3} {DIM_NAMES[d]:4} {c['score']:>3}: " + ' | '.join(parts))
            notes = []
            for k, label in (('same_chroma', '同彩度'), ('same_cr', '同对比度')):
                v = r['diag'].get(k)
                if v is not None:
                    notes.append(f"语法色{label}占比 {v:.0%}{' (压平)' if v > FLAT_SHARE else ''}")
            if m['kind'] == 'vscode':
                notes += fidelity(name, f)
            if notes:
                print('    诊断: ' + ' | '.join(notes))
    if failed:
        print('\n未达标(清晰门禁 CLEAR_GATE 与 color-theme 规范):')
        for f, why in failed:
            print(f'  {f}: ' + '; '.join(why))
        return 1
    if check:
        print('\n全部受检主题达标(清晰门禁)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
