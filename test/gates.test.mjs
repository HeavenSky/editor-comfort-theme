import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { checkConfigDefaults } from "../devkit/check-manifest.mjs";
import deriveAllowlist from "../devkit/vsix-allowlist.mjs";

/**
 * 门禁自身的测试。
 *
 * 门禁漏判不会让构建失败, 只会静默放过它本该拦住的东西, 因此推导规则必须有断言:
 * 允许清单必须涵盖清单里声明的每一类产物, 配置默认值检查必须拦住每一类漂移。
 *
 * 用 `.mjs` 而不是 `.ts`: `tsconfig.json` 没开 `allowJs`, 从 `.ts` 里 import 这些构建脚本
 * 会让 `tsc --noEmit` 报缺声明文件; 反过来 tsc 不收录 `.mjs`, 所以两边都干净。
 */

const basePkg = {
	main: "./out/extension.js",
	browser: "./out/extension.js",
	icon: "media/icon.png",
	l10n: "./l10n",
};

describe("deriveAllowlist", () => {
	it("涵盖入口, 图标, l10n 目录与存在的文档", () => {
		const allowed = deriveAllowlist({
			pkg: basePkg,
			rootEntries: ["README.md", "CHANGELOG.md", "LICENSE.txt", "package.nls.json", "src"],
			l10nEntries: ["bundle.l10n.zh-cn.json"],
		});
		expect([...allowed].sort()).toEqual(
			[
				"LICENSE.txt",
				"changelog.md",
				"l10n/bundle.l10n.zh-cn.json",
				"media/icon.png",
				"package.json",
				"package.nls.json",
				"out/extension.js",
				"readme.md",
			].sort()
		);
	});

	it("不把仓库里没有的文档算进来", () => {
		const allowed = deriveAllowlist({ pkg: basePkg, rootEntries: [], l10nEntries: [] });
		expect(allowed.has("readme.md")).toBe(false);
		expect(allowed.has("NOTICE.md")).toBe(false);
	});

	it("保留 README 的其它语言版本原名", () => {
		const allowed = deriveAllowlist({
			pkg: basePkg,
			rootEntries: ["README.md", "README.zh-cn.md"],
			l10nEntries: [],
		});
		expect(allowed.has("readme.md")).toBe(true);
		expect(allowed.has("README.zh-cn.md")).toBe(true);
	});

	it("涵盖视图容器图标 (与市场图标是不同产物)", () => {
		const allowed = deriveAllowlist({
			pkg: {
				...basePkg,
				contributes: { viewsContainers: { activitybar: [{ icon: "media/panel.svg" }] } },
			},
			rootEntries: [],
			l10nEntries: [],
		});
		expect(allowed.has("media/panel.svg")).toBe(true);
	});

	it("涵盖命令图标, 跳过 $(codicon) 引用", () => {
		const allowed = deriveAllowlist({
			pkg: {
				...basePkg,
				contributes: {
					viewsContainers: { activitybar: [{ icon: "$(git-branch)" }] },
					commands: [
						{ command: "a", icon: "media/a.svg" },
						{
							command: "b",
							icon: { light: "media/b-light.svg", dark: "media/b-dark.svg" },
						},
						{ command: "c", icon: "$(refresh)" },
					],
				},
			},
			rootEntries: [],
			l10nEntries: [],
		});
		expect(allowed.has("media/a.svg")).toBe(true);
		expect(allowed.has("media/b-light.svg")).toBe(true);
		expect(allowed.has("media/b-dark.svg")).toBe(true);
		expect([...allowed].some(entry => entry.includes("$("))).toBe(false);
	});

	it("放行入口同目录下的 .wasm, 但不放行其它生成物", () => {
		const allowed = deriveAllowlist({
			pkg: basePkg,
			rootEntries: [],
			l10nEntries: [],
			outEntries: ["extension.js", "server.wasm", "extension.js.map", "stray.bin"],
		});
		expect(allowed.has("out/server.wasm")).toBe(true);
		expect(allowed.has("out/extension.js.map")).toBe(false);
		expect(allowed.has("out/stray.bin")).toBe(false);
	});

	it("省略 outEntries 时行为不变", () => {
		const allowed = deriveAllowlist({ pkg: basePkg, rootEntries: [], l10nEntries: [] });
		expect([...allowed].some(name => name.endsWith(".wasm"))).toBe(false);
	});

	it("涵盖语言类贡献点引用的文件", () => {
		const allowed = deriveAllowlist({
			pkg: {
				...basePkg,
				contributes: {
					languages: [
						{
							id: "toml",
							configuration: "./language-configuration.json",
							icon: { light: "media/toml-light.svg", dark: "media/toml-dark.svg" },
						},
					],
					grammars: [{ language: "toml", path: "./syntaxes/toml.tmLanguage.json" }],
					snippets: [{ language: "toml", path: "./snippets/toml.json" }],
				},
			},
			rootEntries: [],
			l10nEntries: [],
		});
		expect(allowed.has("language-configuration.json")).toBe(true);
		expect(allowed.has("media/toml-light.svg")).toBe(true);
		expect(allowed.has("media/toml-dark.svg")).toBe(true);
		expect(allowed.has("syntaxes/toml.tmLanguage.json")).toBe(true);
		expect(allowed.has("snippets/toml.json")).toBe(true);
	});

	it("涵盖 Markdown 预览的脚本与样式", () => {
		const allowed = deriveAllowlist({
			pkg: {
				...basePkg,
				contributes: {
					"markdown.previewScripts": [
						"./media/preview/a.js",
						{ path: "./media/preview/b.js", type: "module" },
					],
					"markdown.previewStyles": ["./media/preview/c.css"],
				},
			},
			rootEntries: [],
			l10nEntries: [],
		});
		expect(allowed.has("media/preview/a.js")).toBe(true);
		expect(allowed.has("media/preview/b.js")).toBe(true);
		expect(allowed.has("media/preview/c.css")).toBe(true);
	});

	it("纯主题扩展: 没有 main 时只收主题文件, 不收入口", () => {
		const allowed = deriveAllowlist({
			pkg: {
				icon: "media/icon.png",
				contributes: {
					themes: [
						{ path: "./themes/a-color-theme.json" },
						{ path: "./themes/b-color-theme.json" },
					],
					iconThemes: [{ path: "./icons/icon-theme.json" }],
				},
			},
			rootEntries: ["README.md"],
			l10nEntries: [],
			outEntries: ["extension.wasm"],
		});
		expect([...allowed].sort()).toEqual([
			"icons/icon-theme.json",
			"media/icon.png",
			"package.json",
			"readme.md",
			"themes/a-color-theme.json",
			"themes/b-color-theme.json",
		]);
	});

	it("涵盖 l10n 子目录 (捆绑的第三方语言包)", () => {
		const allowed = deriveAllowlist({
			pkg: basePkg,
			rootEntries: [],
			l10nEntries: ["bundle.l10n.zh-cn.json", "yaml-server/bundle.l10n.json"],
		});
		expect(allowed.has("l10n/bundle.l10n.zh-cn.json")).toBe(true);
		expect(allowed.has("l10n/yaml-server/bundle.l10n.json")).toBe(true);
	});
});

/**
 * 配置默认值自洽检查的样本。写进临时目录而不是读骨架自己的 package.json:
 * 应失败样例必须能独立构造, 不能靠改骨架清单来测。
 */
const tempRoot = properties => {
	const root = mkdtempSync(join(tmpdir(), "vsc-ext-gates-"));
	writeFileSync(
		join(root, "package.json"),
		JSON.stringify({ contributes: { configuration: { properties } } })
	);
	return root;
};

describe("checkConfigDefaults", () => {
	it("完整对齐的 object 配置通过", () => {
		const root = tempRoot({
			"ext.object": {
				type: "object",
				default: { alpha: true, beta: "x" },
				additionalProperties: false,
				properties: {
					alpha: { type: "boolean", default: true },
					beta: { type: "string", default: "x" },
				},
				defaultSnippets: [{ body: { alpha: true, beta: "x" } }, { body: { alpha: false } }],
			},
			"ext.simple": { type: "boolean", default: false },
			// 兼容用的覆盖容器: default: {} 且无 nested properties, 是它的实际默认值。
			"ext.legacy": { type: "object", default: {}, additionalProperties: true },
		});
		expect(checkConfigDefaults(root)).toEqual([]);
	});

	it("检出缺 default, 缺 additionalProperties 与父子 default 不一致", () => {
		const root = tempRoot({
			"ext.missing": { type: "boolean" },
			"ext.object": {
				type: "object",
				default: { alpha: true, extra: 1 },
				properties: {
					alpha: { type: "boolean", default: false },
					beta: { type: "string" },
				},
			},
		});
		const problems = checkConfigDefaults(root);
		expect(problems.some(p => p.includes("ext.missing 缺少 default"))).toBe(true);
		expect(problems.some(p => p.includes("additionalProperties"))).toBe(true);
		expect(problems.some(p => p.includes("nested default 与父 default 不一致: alpha"))).toBe(
			true
		);
		expect(problems.some(p => p.includes("缺少 nested 键: beta"))).toBe(true);
		expect(problems.some(p => p.includes("含有 schema 未声明的键: extra"))).toBe(true);
		expect(problems.some(p => p.includes("ext.object.properties.beta 缺少 default"))).toBe(
			true
		);
	});

	it("全量 defaultSnippets 与 default 不一致时报错, 部分覆盖的 snippet 不报", () => {
		const root = tempRoot({
			"ext.object": {
				type: "object",
				default: { alpha: true, beta: "x" },
				additionalProperties: true,
				properties: {
					alpha: { type: "boolean", default: true },
					beta: { type: "string", default: "x" },
				},
				defaultSnippets: [{ body: { alpha: true, beta: "y" } }],
			},
		});
		expect(checkConfigDefaults(root)).toEqual([
			"ext.object 的全量 defaultSnippets[0] 与 default 不一致",
		]);
	});

	it("多份 configuration (数组形态) 都被检查", () => {
		const root = mkdtempSync(join(tmpdir(), "vsc-ext-gates-"));
		writeFileSync(
			join(root, "package.json"),
			JSON.stringify({
				contributes: {
					configuration: [
						{ properties: { "ext.a": { type: "boolean", default: true } } },
						{ properties: { "ext.b": { type: "string" } } },
					],
				},
			})
		);
		expect(checkConfigDefaults(root)).toEqual(["ext.b 缺少 default"]);
	});
});
