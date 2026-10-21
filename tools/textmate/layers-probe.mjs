// 语法层次探针: 记录语料里每个 token 由主题的哪条选择器决定前景色, 供 tools/gen/separate.py 在没有 VS Code 的环境里按真实分词算层次指标.
// 做法: 每条选择器取一个唯一哨兵色(顺序与原规则相同, 优先级不变), 分词着色后按哨兵色反查; 落在默认色上的记 -1.
// token 元数据里颜色序号只有 9 位(最多 511 色), 选择器分批上哨兵色, 批外的统一用 OTHER; 颜色不影响匹配, 每个 token 只在胜出者所在批里落到唯一色.
// 用法: node tools/textmate/layers-probe.mjs < in.json > out.json
//   输入 {files: [语料路径], themes: {<名>: [选择器...]}}; 输出 {tokens: [[文件序号, 行号, scope 链]], themes: {<名>: [每个 token 的选择器序号]}}
import fs from "node:fs";
import { grammarOf, registry, vsctm } from "./textmate.mjs";

const DEF = "#FE01FE";
const OTHER = "#FE02FE";
const BATCH = 500;
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const grammars = await Promise.all(
	input.files.map(async f => [await grammarOf(f), fs.readFileSync(f, "utf8").split("\n")])
);
// 与 Python 的 \w 同口径(含中文), 只统计带字母数字的 token
const WORD = /[\p{L}\p{N}_]/u;

/** 逐 token 的颜色; scopes 为 true 时同时返回 scope 链(与主题无关) */
function paint(rules, scopes) {
	registry.setTheme({
		name: "layers",
		settings: [{ settings: { foreground: DEF, background: "#000000" } }, ...rules],
	});
	const cmap = registry.getColorMap();
	const out = [];
	grammars.forEach(([grammar, lines], fi) => {
		let stack = vsctm.INITIAL;
		lines.forEach((line, ln) => {
			const r1 = grammar.tokenizeLine(line, stack);
			const r2 = grammar.tokenizeLine2(line, stack);
			stack = r1.ruleStack;
			// tokenizeLine 给 scope 链, tokenizeLine2 给着色结果(二者切分可能不同, 按起点对齐)
			for (const t of r1.tokens) {
				if (!WORD.test(line.slice(t.startIndex, t.endIndex))) continue;
				let m = r2.tokens[1];
				for (let i = 0; i < r2.tokens.length; i += 2)
					if (r2.tokens[i] <= t.startIndex) m = r2.tokens[i + 1];
				out.push({
					color: cmap[(m & 0b00000000111111111000000000000000) >>> 15],
					at: scopes ? [fi, ln + 1, t.scopes] : null,
				});
			}
		});
	});
	return out;
}

const sentinel = i => "#0B" + i.toString(16).toUpperCase().padStart(4, "0");
const result = { tokens: paint([], true).map(t => t.at), themes: {} };
for (const [name, sels] of Object.entries(input.themes)) {
	const back = new Map(sels.map((s, i) => [sentinel(i), i]));
	const hit = Array.from({ length: result.tokens.length }, () => -1);
	for (let lo = 0; lo < Math.max(1, sels.length); lo += BATCH) {
		const rules = sels.map((s, i) => ({
			scope: s,
			settings: { foreground: i >= lo && i < lo + BATCH ? sentinel(i) : OTHER },
		}));
		paint(rules, false).forEach((t, k) => {
			if (back.has(t.color)) hit[k] = back.get(t.color);
		});
	}
	result.themes[name] = hit;
}
process.stdout.write(JSON.stringify(result));
