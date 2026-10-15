// 用 VS Code 自带的语法与 vscode-textmate 主题引擎, 把样例文件逐 token 着色, 输出每个主题下每个 token 的 scope 链, 颜色与字体样式.
// 用法: node tools/textmate/tokenize.mjs <主题目录> <文件>... > out.json   (依赖 devDependencies 里的 vscode-textmate 与 vscode-oniguruma)
import fs from 'node:fs';
import path from 'node:path';
import { grammarOf, registry, vsctm } from './textmate.mjs';

const [themeDir, ...files] = process.argv.slice(2);
const out = {};
for (const tf of fs.readdirSync(themeDir).filter((f) => f.endsWith('.json')).sort()) {
  const theme = JSON.parse(fs.readFileSync(path.join(themeDir, tf), 'utf8'));
  const settings = [{ settings: { foreground: theme.colors['editor.foreground'], background: theme.colors['editor.background'] } }, ...theme.tokenColors];
  registry.setTheme({ name: theme.name, settings });
  const cmap = registry.getColorMap();
  const name = tf.replace(/\.json$/, '');
  out[name] = { bg: theme.colors['editor.background'], fg: theme.colors['editor.foreground'], files: {} };
  for (const f of files) {
    const grammar = await grammarOf(f);
    let rule = vsctm.INITIAL;
    const toks = [];
    fs.readFileSync(f, 'utf8').split('\n').forEach((line, ln) => {
      const r1 = grammar.tokenizeLine(line, rule);
      const r2 = grammar.tokenizeLine2(line, rule);
      // tokenizeLine 给 scope 链, tokenizeLine2 给着色结果(二者切分可能不同, 按起点对齐)
      const meta = [];
      for (let i = 0; i < r2.tokens.length; i += 2) meta.push([r2.tokens[i], r2.tokens[i + 1]]);
      for (const t of r1.tokens) {
        const text = line.slice(t.startIndex, t.endIndex);
        if (!text.trim()) continue;
        let m = meta[0][1];
        for (const [s, v] of meta) if (s <= t.startIndex) m = v;
        const fgIdx = (m & 0b00000000111111111000000000000000) >>> 15;
        const fs_ = (m & 0b00000000000000000111100000000000) >>> 11;
        toks.push({ ln: ln + 1, text, scopes: t.scopes, color: cmap[fgIdx], bold: !!(fs_ & 2), italic: !!(fs_ & 1) });
      }
      rule = r1.ruleStack;
    });
    out[name].files[path.basename(f)] = toks;
  }
}
process.stdout.write(JSON.stringify(out));
