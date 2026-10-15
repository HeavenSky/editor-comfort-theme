# /// script
# requires-python = ">=3.11"
# ///
# 颜色键分层核对: 按普查实测, 列出每个颜色键在参考主题里的相对指标中位数与所在档目标的偏离, 以及同一梯子上离它最近的档; 复核 tools/lab/key-levels.mjs 的归属时用.
# 只是线索: 实测值接近别的档不等于归错, 按语义确实归错才改规则(例: 当前行号实测与正文同亮, 留内容强).
# 数据来自标定台(先运行 node tools/lab/threshold-lab.mjs serve <标定目录>); 参考主题取 assets/levels.json 的 ref.
# 用法: uv run tools/lab/lab_key_fit.py [--url http://127.0.0.1:9340] [--min-themes 3]
import json, os, statistics as S, sys, urllib.request
from collections import defaultdict

URL = sys.argv[sys.argv.index('--url') + 1] if '--url' in sys.argv else 'http://127.0.0.1:9340'
MIN_THEMES = int(sys.argv[sys.argv.index('--min-themes') + 1]) if '--min-themes' in sys.argv else 3
LEVELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'levels.json')
LADDERS = [['内容强', '内容中', '内容弱', '暗化强', '暗化中', '暗化弱'], ['线条强', '线条中', '线条弱'], ['底色强', '底色中', '底色弱']]


def tmean(v: list[float]) -> float:
    """20% 截尾均值, 与标定台推荐目标的算法一致."""
    v = sorted(v)
    c = int(len(v) * 0.2)
    return S.mean(v[c:len(v) - c] if len(v) > 4 else v)


def main() -> int:
    d = json.load(urllib.request.urlopen(f'{URL}/data.json', timeout=60))
    ref = set(json.load(open(LEVELS, encoding='utf-8')).get('ref') or [])
    lad = {k: L for L in LADDERS for k in L}
    by = defaultdict(lambda: defaultdict(list))
    lv = defaultdict(lambda: defaultdict(list))
    for it in d['items']:
        if it['theme'] in ref:
            lv[it['level']][it['theme']].append(it['rd'])
        if it.get('key') and it['key'] != '(语法色)' and not it.get('keyNote'):
            by[(it['key'], it['level'])][it['theme']].append(it['rd'])
    target = {k: tmean([S.median(v) for v in t.values()]) for k, t in lv.items() if t}
    print('各档目标(参考主题):', {k: round(v, 1) for k, v in sorted(target.items())})
    rows = []
    for (key, level), per in by.items():
        if level not in lad or len(per) < MIN_THEMES:
            continue
        refm = [S.median(v) for t, v in per.items() if t in ref]
        m = S.median(refm or [S.median(v) for v in per.values()])
        near = min(lad[level], key=lambda k: abs(target.get(k, 1e9) - m))
        if near != level:
            rows.append((abs(m - target[level]), key, level, m, len(refm), len(per), near))
    print('偏离 | 键 | 当前档 | 参考中位 rd | 参考主题数 | 全部主题数 | 最近档(目标)')
    for dev, key, level, m, nr, na, near in sorted(rows, reverse=True):
        print(f'{dev:.0f} | {key} | {level} | {m:.1f} | {nr} | {na} | {near}({target[near]:.1f})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
