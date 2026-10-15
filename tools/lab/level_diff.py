# /// script
# requires-python = ">=3.11"
# ///
# 调色改动对比: 当前 themes/ 与某个提交里的 themes/ 相比, 每套主题相对原色(补全段的中间主题 assets/full-theme/<name>-full.json)改了多少键,
# 哪些键比旧版还原成了原色, 哪些是新改的(附所在分层); 改调色步骤或门槛后核对"认可的主题少动, 问题主题多修"用.
# 中间主题由 complete.py 生成, 不在版本库里的先运行 npm run gen:themes.
# 用法: uv run tools/lab/level_diff.py [--ref HEAD] [--out <文件.md>]   (不写 --out 只打印每套主题的汇总)
import json, os, subprocess, sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REF = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else 'HEAD'
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None


def main() -> int:
    doc = json.load(open(os.path.join(ROOT, 'assets/levels.json'), encoding='utf-8'))
    ref, kl = set(doc.get('ref') or []), doc['keyLevels']
    names = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, 'themes')) if f.endswith('.json'))
    names.sort(key=lambda n: (n not in ref, n))
    summary, detail = [], []
    for n in names:
        shown = subprocess.run(['git', 'show', f'{REF}:themes/{n}.json'], cwd=ROOT, capture_output=True, text=True)
        old = json.loads(shown.stdout)['colors'] if shown.returncode == 0 else {}
        new = json.load(open(os.path.join(ROOT, 'themes', f'{n}.json'), encoding='utf-8'))['colors']
        full = json.load(open(os.path.join(ROOT, 'assets/full-theme', f'{n}-full.json'), encoding='utf-8'))['colors']
        back = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k) and new.get(k) == full.get(k))
        chg = sorted(k for k in new if new.get(k) != old.get(k) and new.get(k) != full.get(k))
        n_old = sum(1 for k in old if old.get(k) != full.get(k))
        n_new = sum(1 for k in new if new.get(k) != full.get(k))
        star = '★' if n in ref else ' '
        summary.append(f'{star} {n:14} 相对原色改动键: {REF} {n_old:3} -> 当前 {n_new:3} | 还原 {len(back):2} 个, 新改 {len(chg):2} 个')
        detail.append(f'## {star} {n}: 还原原色 {len(back)} 个键, 新改动 {len(chg)} 个键')
        detail += [f'- 还原 `{k}` {old.get(k)} -> 原色 {full.get(k)} ({kl.get(k, "-")})' for k in back]
        detail += [f'- 新改 `{k}` 原色 {full.get(k)} -> {new.get(k)} ({REF}: {old.get(k)}) ({kl.get(k, "-")})' for k in chg]
    print('\n'.join(summary))
    if OUT:
        open(OUT, 'w', encoding='utf-8').write('★ 为参考主题(assets/levels.json 的 ref)\n\n' + '\n'.join(summary) + '\n\n' + '\n'.join(detail) + '\n')
        print('明细 ->', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
