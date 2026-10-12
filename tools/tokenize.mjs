// 用 VS Code 自带的语法与 vscode-textmate 主题引擎, 把样例文件逐 token 着色, 输出每个主题下每个 token 的 scope 链, 颜色与字体样式.
// 用法: node tools/tokenize.mjs <主题目录> <文件>... > out.json   (依赖 devDependencies 里的 vscode-textmate 与 vscode-oniguruma)
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import vsctm from 'vscode-textmate';
import oniguruma from 'vscode-oniguruma';

const require = createRequire(import.meta.url);
// VS Code 安装位置: 环境变量 VSCODE_APP, 默认 macOS 的标准位置
const APP = process.env.VSCODE_APP || '/Applications/Visual Studio Code.app';
const EXT = path.join(APP, 'Contents/Resources/app/extensions');
const wasm = fs.readFileSync(path.join(path.dirname(require.resolve('vscode-oniguruma')), 'onig.wasm')).buffer;
await oniguruma.loadWASM(wasm);
const onigLib = Promise.resolve({ createOnigScanner: (s) => new oniguruma.OnigScanner(s), createOnigString: (s) => new oniguruma.OnigString(s) });

// scopeName -> 语法文件; 语言 id / 扩展名 -> scopeName
const byScope = {}, byExt = {}, injections = {};
for (const dir of fs.readdirSync(EXT)) {
  const pj = path.join(EXT, dir, 'package.json');
  if (!fs.existsSync(pj)) continue;
  const c = JSON.parse(fs.readFileSync(pj, 'utf8')).contributes || {};
  const langExt = {};
  for (const l of c.languages || []) for (const e of l.extensions || []) langExt[e] = l.id;
  for (const g of c.grammars || []) {
    byScope[g.scopeName] = path.join(EXT, dir, g.path);
    if (g.language) for (const [e, id] of Object.entries(langExt)) if (id === g.language) byExt[e] = g.scopeName;
    for (const t of g.injectTo || []) (injections[t] ||= []).push(g.scopeName);
  }
}

const registry = new vsctm.Registry({
  onigLib,
  loadGrammar: async (scope) => {
    const p = byScope[scope];
    if (!p) return null;
    return vsctm.parseRawGrammar(fs.readFileSync(p, 'utf8'), p);
  },
  getInjections: (scope) => injections[scope],
});

const [themeDir, ...files] = process.argv.slice(2);
const out = {};
for (const tf of fs.readdirSync(themeDir).filter((f) => f.endsWith('.json')).sort()) {
  const theme = JSON.parse(fs.readFileSync(path.join(themeDir, tf), 'utf8'));
  const settings = [{ settings: { foreground: theme.colors['editor.foreground'], background: theme.colors['editor.background'] } }, ...theme.tokenColors];
  registry.setTheme({ name: theme.name, settings });
  const cmap = registry.getColorMap();
  const name = tf.replace('-color-theme.json', '');
  out[name] = { bg: theme.colors['editor.background'], fg: theme.colors['editor.foreground'], files: {} };
  for (const f of files) {
    const scope = byExt[path.extname(f)];
    const grammar = await registry.loadGrammar(scope);
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
