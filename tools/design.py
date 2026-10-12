# /// script
# requires-python = ">=3.11"
# ///
# 设计主题的原主题生成脚本: 以开源深色原主题为模板, 按每套手定的色板逐色换色, 写到 tools/sources/<name>.json,
# 之后与其他原主题一样经 themes.py / gen_vscode.py 做护眼适配. 多数是浅色版(明暗反转); dark=True 的设计只换色相与色板, 不反转.
#
# 换色规则(recolor):
#   1. 与色板里某个深色(PALETTE 的键)色差 < NEAR_DE: 换成对应的颜色, 原色比色板色亮多少, 浅色版就暗多少(明暗反转; 深色设计同向), 色相不变
#   2. 彩色(彩度 > ACCENT_CHROMA): 色相不变, 浅色设计里明度落到浅色彩色带(ACCENT_L 附近, 原色越亮越深), 彩度略收; 深色设计原样保留
#   3. 中性色: 明度按"深色底 -> 浅色底, 深色正文 -> 浅色正文"线性映射, 色相与(收窄的)彩度跟随浅色底
#   透明度原样保留. tokenColors 的结构与模板完全相同, 规则池(pool.py)按结构去重, 浅色版不额外投票, 其他主题不受影响.
#   终端黑白四色按浅色口径单独给(黑 = 正文, 白 = 浅灰, 亮白 = 比底更亮), 不走反转.
#
# 用法: uv run tools/design.py           生成全部
#       uv run tools/design.py --check   只比对, 与现有文件不一致时退出码 1
import json, math, os, re, sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import de2000, from_oklch, h, hx, oklch

SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources')
NEAR_DE, ACCENT_CHROMA, ACCENT_L = 8.0, 0.07, 0.52

DESIGNS = [
    # ---- Moka Light: 经典 Monokai 色板(Wimer Hazenberg)的浅色版, 与 Comfort Moka Dark(One Monokai)成对; 结构取 One Monokai(MIT), 其 One Dark 系颜色按角色换成 Monokai 色相.
    #      底取 Monokai 的正文色 #F8F8F2(暖白), 正文取 Monokai 的底色 #272822, 彩色压深到浅底可读 ----
    dict(name='moka-light', label='Moka Light', template='moka-dark.json',
         bg='#F8F8F2', fg='#272822',
         palette={
             '#282C34': '#F8F8F2',  # 底
             '#ABB2BF': '#272822',  # 正文
             '#676F7D': '#8A8571',  # 注释(Monokai #75715E 提亮)
             '#E06C75': '#C7245E',  # 关键字 / 标签: Monokai 粉 #F92672
             '#E5C07B': '#958312',  # 字符串: Monokai 黄 #E6DB74
             '#C678DD': '#7A4FD6',  # 数字 / 常量: Monokai 紫 #AE81FF
             '#56B6C2': '#1A8BA3',  # 声明类型 / 对象键: Monokai 青 #66D9EF
             '#61AFEF': '#2F72B5',  # 类型: 青偏蓝, 与声明类型的青分开
             '#98C379': '#5B8C0A',  # 函数 / 属性名: Monokai 绿 #A6E22E
             '#D19A66': '#C0650C',  # 参数: Monokai 橙 #FD971F
             '#528BFF': '#2F72B5',  # 光标 / 强调蓝
             '#F44747': '#C8302C',  # 错误红
             '#C24038': '#C8302C',
             '#7E0097': '#7A4FD6',
             '#F8F8F0': '#C8302C',  # 原版 invalid 的白字(配红底), 浅色里直接用错误红
         },
         ansi=dict(Black='#272822', BrightBlack='#8A8571', White='#D6D5CC', BrightWhite='#FDFDF8')),

    # ---- Dracula Light: Dracula 官方浅色色板 Alucard(draculatheme.com/spec, MIT); 结构取 Dracula Soft ----
    dict(name='dracula-light', label='Dracula Light', template='dracula-dark.json',
         bg='#FFFBEB', fg='#1F1F1F',
         palette={
             '#282A36': '#FFFBEB',  # Background
             # 深色版里比底更深的面板(侧栏, 标签栏, 状态栏)在浅色版里比底稍暗一点, 不反转成更亮
             '#262626': '#F3EFDC', '#21222C': '#F1EDDA', '#191A21': '#EDE9D5', '#343746': '#EAE6D4',
             '#44475A': '#CFCFDE',  # Current Line / Selection
             '#F6F6F4': '#1F1F1F', '#FFFFFF': '#1F1F1F',  # Foreground
             '#7B7F8B': '#6C664B',  # Comment
             '#97E1F1': '#036A96', '#8BE9FD': '#036A96', '#ADF6F6': '#036A96',  # Cyan
             '#BF9EEE': '#644AC9', '#BD93F9': '#644AC9', '#D6B4F7': '#644AC9',  # Purple
             '#F286C4': '#A3144D', '#FF79C6': '#A3144D', '#F49DDA': '#A3144D',  # Pink
             '#FFB86C': '#A34D14',  # Orange
             '#EE6666': '#CB3A2A', '#FF5555': '#CB3A2A', '#F07C7C': '#CB3A2A',  # Red
             '#62E884': '#14710A', '#50FA7B': '#14710A', '#78F09A': '#14710A',  # Green
             '#E7EE98': '#846E15', '#F1FA8C': '#846E15', '#F6F6AE': '#846E15', '#DEE492': '#846E15',  # Yellow
         },
         ansi=dict(Black='#1F1F1F', BrightBlack='#6C664B', White='#DCD8C6', BrightWhite='#FFFDF5')),

    # ---- Pale Light: Palenight(MIT)色相的浅色版, 原版没有浅色; 底取明显的淡薰衣草色, 正文取偏紫的深靛;
    #      关键字偏玫紫, 函数偏靛蓝, 与中性灰底, 紫关键字, 蓝函数的 Owl Light 拉开 ----
    dict(name='pale-light', label='Pale Light', template='pale-dark.json',
         bg='#EFE9F9', fg='#342F5C',
         palette={
             '#292D3E': '#EFE9F9',  # 底
             '#BFC7D5': '#342F5C', '#A6ACCD': '#342F5C',  # 正文
             '#EEFFFF': '#262A44', '#FFFFFF': '#262A44',  # 高亮白字 -> 最深的字
             '#676E95': '#8A8EAE', '#697098': '#8A8EAE',  # 注释
             '#C792EA': '#A23E9E',  # 关键字: 玫紫
             '#C3E88D': '#5A8A1C', '#A9C77D': '#5A8A1C',  # 字符串绿
             '#F78C6C': '#C04F2A',  # 数字橙
             '#82AAFF': '#4B4FCB', '#82B1FF': '#4B4FCB',  # 函数: 靛蓝
             '#FFCB6B': '#A06C00', '#FFCA28': '#A06C00',  # 类型 / 变量黄
             '#89DDFF': '#1C80AE',  # 运算符 / 属性天蓝
             '#FF5572': '#C93652', '#FF5370': '#C93652', '#FF5874': '#C93652', '#EF5350': '#C93652',  # 红
             '#80CBC4': '#24857D',  # 对象键 / 行内代码青
             '#7986E7': '#5560C8',  # 参数
             '#7E57C2': '#6C48B0',  # 界面强调紫
             '#FF869A': '#BF4566',  # 链接
             '#FFEB95': '#8A7410',
         },
         ansi=dict(Black='#342F5C', BrightBlack='#8A8EAE', White='#D6D0E6', BrightWhite='#FBF9FE')),
]

ANSI_GRAYS = ['Black', 'BrightBlack', 'White', 'BrightWhite']


def load(path: str) -> dict:
    s = open(path, encoding='utf-8').read()
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', re.sub(r'^\s*//.*$', '', s, flags=re.M)))


def split(v: str):
    """'#RGB' / '#RGBA' / '#RRGGBB' / '#RRGGBBAA' -> (rgb, alpha 两位十六进制或 '')."""
    s = v.lstrip('#')
    if len(s) in (3, 4):
        s = ''.join(ch * 2 for ch in s)
    return h(s[:6]), s[6:8].upper()


class Recolor:
    def __init__(self, d: dict, src_bg: str, src_fg: str):
        self.pal = [(h(k[1:]), h(v[1:])) for k, v in d['palette'].items()]
        self.dbg, self.dfg = oklch(h(src_bg.lstrip('#')[:6])), oklch(h(src_fg.lstrip('#')[:6]))
        self.lbg, self.lfg = oklch(h(d['bg'][1:])), oklch(h(d['fg'][1:]))
        self.dark = d.get('dark', False)

    def rgb(self, c):
        L, C, H = oklch(c)
        near, de = min(((p, de2000(c, p[0])) for p in self.pal), key=lambda x: x[1])
        if de < NEAR_DE:
            Ld = L - oklch(near[0])[0]
            Ll, Cl, Hl = oklch(near[1])
            return from_oklch(min(0.98, max(0.05, Ll + Ld if self.dark else Ll - Ld)), Cl, Hl)
        if C > ACCENT_CHROMA:
            if self.dark:
                return c
            return from_oklch(min(0.62, max(0.40, ACCENT_L - (L - 0.75) * 0.5)), C * 0.85, H)
        # 中性色: 深色底 -> 浅色底, 深色正文 -> 浅色正文 的线性映射(两端外推后夹住)
        span = self.dfg[0] - self.dbg[0]
        t = (L - self.dbg[0]) / span if abs(span) > 1e-6 else 0
        Ln = min(0.99, max(0.08, self.lbg[0] + t * (self.lfg[0] - self.lbg[0])))
        # 彩度: 贴近底的取浅色底的色调, 贴近正文的取浅色正文的色调
        w = min(1, max(0, t))
        Cn = min(C, 0.03) * 0.5 + (self.lbg[1] * (1 - w) + self.lfg[1] * w)
        Hn = self.lbg[2] if w < 0.5 else self.lfg[2]
        return from_oklch(Ln, min(Cn, 0.04), Hn)

    def __call__(self, v):
        if not isinstance(v, str) or not v.startswith('#') or len(v) not in (4, 5, 7, 9):
            return v
        rgb, alpha = split(v)
        return hx(self.rgb(rgb)) + alpha


def design(d: dict) -> dict:
    src = load(os.path.join(SOURCES, d['template']))
    c = src['colors']
    from gen_vscode import source_fg
    rc = Recolor(d, c['editor.background'], source_fg(src, True))
    colors = {k: rc(v) for k, v in c.items()}
    colors['editor.background'], colors['editor.foreground'] = d['bg'], d['fg']
    for n in ANSI_GRAYS:
        colors['terminal.ansi' + n] = d['ansi'][n]
    rules = []
    for r in src.get('tokenColors', []):
        r = json.loads(json.dumps(r))
        st = r.get('settings', {})
        for k in ('foreground', 'background'):
            if k in st:
                st[k] = rc(st[k])
        rules.append(r)
    out = {'name': d['label'], 'type': 'dark' if d.get('dark') else 'light',
           '$comment': f"由 tools/design.py 以 {d['template']} 为模板生成, 不要手改",
           'colors': colors, 'tokenColors': rules}
    if 'semanticHighlighting' in src:
        out['semanticHighlighting'] = src['semanticHighlighting']
    if src.get('semanticTokenColors'):
        out['semanticTokenColors'] = {k: rc(v) if isinstance(v, str) else
                                      {**v, **({'foreground': rc(v['foreground'])} if 'foreground' in v else {})}
                                      for k, v in src['semanticTokenColors'].items()}
    return out


def main() -> int:
    check = '--check' in sys.argv
    stale = []
    for d in DESIGNS:
        path = os.path.join(SOURCES, d['name'] + '.json')
        text = json.dumps(design(d), indent=4, ensure_ascii=False) + '\n'
        old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if old == text:
            continue
        if check:
            stale.append(os.path.relpath(path))
        else:
            open(path, 'w', encoding='utf-8').write(text)
            print('wrote', os.path.relpath(path))
    if stale:
        print('与 tools/design.py 不一致, 先运行 uv run tools/design.py:', *stale, sep='\n  ')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
