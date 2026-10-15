// VS Code 自带语法 + vscode-textmate 主题引擎的公共初始化, 供 tokenize.mjs 与 pool-guard.mjs 共用.
// VS Code 安装位置: 环境变量 VSCODE_APP, 默认 macOS 的标准位置(依赖 devDependencies 里的 vscode-textmate 与 vscode-oniguruma)
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import vsctm from 'vscode-textmate';
import oniguruma from 'vscode-oniguruma';

export { vsctm };
const require = createRequire(import.meta.url);
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

export const registry = new vsctm.Registry({
  onigLib,
  loadGrammar: async (scope) => {
    const p = byScope[scope];
    if (!p) return null;
    return vsctm.parseRawGrammar(fs.readFileSync(p, 'utf8'), p);
  },
  getInjections: (scope) => injections[scope],
});

/** 按扩展名加载文件对应的语法 */
export const grammarOf = (file) => registry.loadGrammar(byExt[path.extname(file)]);
