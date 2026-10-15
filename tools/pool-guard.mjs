// 规则池分词实测: 找出会改掉原主题已上色 token 颜色的池选择器. 静态只看选择器判断不了 token 套在哪些外层 scope 里
// (如 One Light 的 Less @primary 靠外层 variable 规则上色, 补上内层 support.other.variable.less 后改了色), 这里用真实语法分词来判.
// 做法: 原主题规则单独着色, 默认色取哨兵, 不是哨兵的字符即原主题已上色; 再把池选择器各取一个唯一哨兵色放在最前(与补全段同序)着色,
// 已上色的字符落到池哨兵色上, 对应选择器剔除; 剔除后可能露出下一条池规则, 重复到没有为止. 只覆盖样例文件里出现的语法.
// 用法: node tools/pool-guard.mjs < in.json > out.json
//   输入 {files: [样例路径], themes: {<名>: {rules: 原主题 tokenColors, pool: [池选择器]}}}; 输出 {<名>: [剔除的选择器]}
import fs from 'node:fs';
import { grammarOf, registry, vsctm } from './textmate.mjs';

const DEF = '#FE01FE';
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const grammars = await Promise.all(input.files.map(async (f) => [await grammarOf(f), fs.readFileSync(f, 'utf8').split('\n')]));

/** 逐字符颜色: [文件][行] -> 每个非空白字符的颜色(空白记 null) */
function paint(rules) {
  registry.setTheme({ name: 'guard', settings: [{ settings: { foreground: DEF, background: '#000000' } }, ...rules] });
  const cmap = registry.getColorMap();
  return grammars.map(([grammar, lines]) => {
    let stack = vsctm.INITIAL;
    return lines.map((line) => {
      const r = grammar.tokenizeLine2(line, stack);
      stack = r.ruleStack;
      const out = new Array(line.length).fill(null);
      for (let i = 0; i < r.tokens.length; i += 2) {
        const end = i + 2 < r.tokens.length ? r.tokens[i + 2] : line.length;
        const color = cmap[(r.tokens[i + 1] & 0b00000000111111111000000000000000) >>> 15];
        for (let j = r.tokens[i]; j < end; j++) if (line[j].trim()) out[j] = color;
      }
      return out;
    });
  });
}

// 原主题规则只留有前景色且有 scope 的(无 scope 的是全局默认色, 交给哨兵)
const own = (rules) =>
  rules.filter((r) => r.scope && r.settings && r.settings.foreground).map((r) => ({ scope: r.scope, settings: { foreground: r.settings.foreground } }));

const result = {};
for (const [name, { rules, pool }] of Object.entries(input.themes)) {
  const base = own(rules);
  const orig = paint(base);
  const sentinel = (i) => '#0A' + i.toString(16).toUpperCase().padStart(4, '0');
  const live = new Set(pool), dropped = [];
  for (;;) {
    const sels = pool.filter((s) => live.has(s));
    const bySentinel = new Map(sels.map((s, i) => [sentinel(i), s]));
    const full = paint([...sels.map((s, i) => ({ scope: s, settings: { foreground: sentinel(i) } })), ...base]);
    const hit = new Set();
    full.forEach((file, fi) => file.forEach((line, li) => line.forEach((c, j) => {
      if (c && orig[fi][li][j] !== DEF && bySentinel.has(c)) hit.add(bySentinel.get(c));
    })));
    if (!hit.size) break;
    for (const s of hit) live.delete(s), dropped.push(s);
  }
  result[name] = dropped.sort();
}
process.stdout.write(JSON.stringify(result));
