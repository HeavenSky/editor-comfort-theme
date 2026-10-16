import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { calibrateByKeys, median, quantile, rulePairs, tmean } from "../tools/lab/rule-pairs.mjs";

/**
 * 分层门槛的覆盖补齐: 普查覆盖不到的颜色键按语义推配对底色键, 普查样本为 0 的级按颜色键标定.
 *
 * 配对推错不会让生成失败, 只会让 level_floor 拿错底色去判, 静默改坏原设计(如把与活动标签底同色的 tab.activeBorder 描出来),
 * 所以规则与导出的 assets/levels.json 都要有断言.
 */

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const registry = new Set(Object.keys(JSON.parse(readFileSync(join(ROOT, "assets/vscode/color-registry.json"), "utf8")).colors));
const levels = JSON.parse(readFileSync(join(ROOT, "assets/levels.json"), "utf8"));
const levelOf = (k) => levels.keyLevels[k] || "";

describe("rulePairs", () => {
	const pairs = rulePairs(
		[
			"input.placeholderForeground",
			"notifications.foreground",
			"notificationsErrorIcon.foreground",
			"editorSuggestWidget.selectedForeground",
			"editorHoverWidget.border",
			"peekViewEditor.matchHighlightBackground",
			"diffEditor.insertedTextBackground",
			"editorOverviewRuler.errorForeground",
			"statusBarItem.warningHoverForeground",
			"tab.activeBackground",
			"titleBar.activeBackground",
			"terminal.ansiRed",
			"editor.background",
		],
		registry,
		levelOf,
	);

	it("明确表: 占位字, 通知图标, peek 匹配高亮, diff 底色", () => {
		expect(pairs["input.placeholderForeground"]).toEqual(["input.background"]);
		expect(pairs["notificationsErrorIcon.foreground"]).toEqual(["notifications.background"]);
		expect(pairs["peekViewEditor.matchHighlightBackground"]).toEqual(["peekViewEditor.background"]);
		expect(pairs["diffEditor.insertedTextBackground"]).toEqual(["editor.background"]);
	});

	it("命名约定: 同状态的底色优先, 再退到同前缀底色与所在容器", () => {
		expect(pairs["notifications.foreground"]).toEqual(["notifications.background"]);
		expect(pairs["editorSuggestWidget.selectedForeground"]).toEqual(["editorSuggestWidget.selectedBackground", "editorSuggestWidget.background"]);
		expect(pairs["editorHoverWidget.border"]).toEqual(["editorHoverWidget.background", "editor.background"]);
		expect(pairs["statusBarItem.warningHoverForeground"]).toEqual(["statusBarItem.warningHoverBackground", "statusBar.background"]);
		expect(pairs["editorOverviewRuler.errorForeground"][0]).toBe("editorOverviewRuler.background");
	});

	it("层次底不按命名约定配对(常与编辑区底故意同色), 终端色与基准不配", () => {
		for (const k of ["tab.activeBackground", "titleBar.activeBackground", "terminal.ansiRed", "editor.background"]) expect(pairs[k]).toBeUndefined();
	});

	it("只采用注册表里存在的底色键, 不配自己", () => {
		for (const [k, us] of Object.entries(pairs)) {
			expect(us.length).toBeGreaterThan(0);
			for (const u of us) {
				expect(registry.has(u)).toBe(true);
				expect(u).not.toBe(k);
			}
		}
	});
});

describe("calibrateByKeys", () => {
	it("统计口径同标定台: 中位数, 20% 截尾均值, 取整分位", () => {
		expect(median([3, 1, 2])).toBe(2);
		expect(median([4, 1, 2, 3])).toBe(2.5);
		expect(tmean([0, 10, 10, 10, 100])).toBe(10);
		expect(quantile([1, 2, 3, 4, 5], 0.05)).toBe(1);
	});

	it("目标按主题等权, 绝对下限不高于规范值", () => {
		const samples = [
			{ theme: "a", rd: 40, abs: 12 },
			{ theme: "a", rd: 60, abs: 14 },
			{ theme: "b", rd: 30, abs: 4 },
		];
		const r = calibrateByKeys(samples, 10);
		expect(r).toMatchObject({ pct: 40, lo: 30, abs: 4, n: 3, themes: 2 });
		expect(calibrateByKeys([], 10)).toBeNull();
	});
});

describe("assets/levels.json", () => {
	it("每个配对都标明来源, 底色键都在注册表里", () => {
		for (const [k, us] of Object.entries(levels.pairs)) {
			expect(["census", "rule"]).toContain(levels.pairsFrom[k]);
			for (const u of us) expect(registry.has(u)).toBe(true);
		}
	});

	it("覆盖缺口已补: 截图之外的场景有配对, 线条中按颜色键标定", () => {
		for (const k of ["input.placeholderForeground", "notifications.foreground", "editorSuggestWidget.foreground", "editorHoverWidget.foreground", "diffEditor.insertedTextBackground", "menu.foreground"]) {
			expect(levels.pairs[k]).toBeDefined();
		}
		expect(levels.levels["线条中"].source).toMatch(/^keys/);
	});

	it("各组梯子有序: 强 > 中 > 弱的目标, 修复下限不高于混档线", () => {
		for (const g of ["线条", "底色"]) {
			const [s, m, w] = ["强", "中", "弱"].map((l) => levels.levels[g + l]);
			expect(s.pct).toBeGreaterThan(m.pct);
			expect(m.pct).toBeGreaterThan(w.pct);
		}
		for (const lv of Object.values(levels.levels)) if (lv.mixLo != null) expect(lv.lo).toBeLessThanOrEqual(lv.mixLo);
	});

	it("同色豁免: unfocused 不算焦点框, 可辨差以下的线保持原主题值", () => {
		const exempt = new RegExp(levels.exemptSameColor, "i");
		expect(exempt.test("focusBorder")).toBe(true);
		expect(exempt.test("list.inactiveFocusOutline")).toBe(true);
		expect(exempt.test("tab.unfocusedActiveBorder")).toBe(false);
		expect(levels.sameColorDE).toBe(2);
		const colorsOf = (p) => JSON.parse(readFileSync(join(ROOT, p), "utf8").replace(/^\s*\/\/.*$/gm, "")).colors;
		for (const [theme, key] of [
			["github-dark", "tab.unfocusedActiveBorder"],
			["pale-dark", "tab.activeBorder"],
			["pale-light", "editorGroupHeader.tabsBorder"],
		]) {
			expect(colorsOf(`themes/${theme}.json`)[key].toUpperCase()).toBe(colorsOf(`assets/source/${theme}.json`)[key].toUpperCase());
		}
	});
});
