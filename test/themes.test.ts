// 校验清单声明的每个颜色主题: 文件存在, 明暗类型与 uiTheme 一致, 颜色值都是合法的十六进制.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
const contributed: { label: string; uiTheme: string; path: string }[] = pkg.contributes.themes;
const HEX = /^#([0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/;

describe.each(contributed)("$label", ({ uiTheme, path }) => {
	const file = join(ROOT, path);

	it("主题文件存在", () => {
		expect(existsSync(file)).toBe(true);
	});

	const theme = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : {};

	it("type 与清单的 uiTheme 一致", () => {
		expect(theme.type).toBe(uiTheme === "vs" ? "light" : "dark");
	});

	it("界面色, 语法色与语义色都是合法的十六进制", () => {
		const values = [
			...Object.values(theme.colors ?? {}),
			...(theme.tokenColors ?? []).map((rule: { settings: { foreground?: string } }) => rule.settings.foreground).filter(Boolean),
			// 语义色有两种写法: "#RRGGBB" 或 { foreground, fontStyle }
			...Object.values(theme.semanticTokenColors ?? {})
				.map(value => (typeof value === "string" ? value : (value as { foreground?: string }).foreground))
				.filter(Boolean),
		];
		expect(values.length).toBeGreaterThan(0);
		expect(values.filter(value => !HEX.test(String(value)))).toEqual([]);
	});

	it("覆盖编辑区与 16 色终端", () => {
		const colors = theme.colors ?? {};
		for (const key of ["editor.background", "editor.foreground", "terminal.background", "terminal.foreground"]) {
			expect(colors).toHaveProperty([key]);
		}
		const ansi = Object.keys(colors).filter(key => /^terminal\.ansi/.test(key));
		expect(ansi).toHaveLength(16);
	});
});
