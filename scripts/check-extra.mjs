/**
 * 本插件专属的发布前门禁: 中间主题与主题生成物未漂移, 全关时没有未登记的改色, 配色清晰门禁达标(其余配色指标只作参考报告)。
 *
 * 各项都要调用 `tools/` 下的 Python 脚本(经 `uv run`); 环境里没有 uv 时打印提示并跳过,
 * 主题文件的结构校验仍由 `test/themes.test.ts` 在任何环境里覆盖。
 */
import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { join } from "node:path";

// uv 首次运行要解析并安装脚本依赖(pyobjc), 取宽值; 之后命中缓存只需数秒。
const UV_TIMEOUT_MS = 5 * 60_000;

function hasUv() {
	try {
		execFileSync("uv", ["--version"], { stdio: "pipe", timeout: 10_000 });
		return true;
	} catch {
		return false;
	}
}

function runUv(root, args, env = {}) {
	try {
		execFileSync("uv", ["run", "-q", ...args], { cwd: root, stdio: "pipe", timeout: UV_TIMEOUT_MS, env: { ...process.env, ...env } });
		return [];
	} catch (error) {
		const output = [error.stdout, error.stderr].map(chunk => (chunk ? chunk.toString().trim() : "")).filter(Boolean);
		return [output.join("\n") || error.message];
	}
}

export default function checks(root) {
	if (!hasUv()) {
		console.log("skip  主题生成物与配色指标检查 (未安装 uv)");
		return {};
	}
	const files = dir => readdirSync(join(root, dir)).map(name => join(dir, name));
	return {
		"设计主题的原主题与 tools/design.py 一致": () => runUv(root, ["tools/design.py", "--check"]),
		// 补全段先写出中间主题(<name>-full.json, 只有 one-dark 的进版本库并在此核对), 后面两项都读它
		"补全的中间主题与 tools/complete.py 一致": () => runUv(root, ["tools/complete.py", "--check"]),
		"主题生成物与 tools/themes.py 一致": () => runUv(root, ["tools/gen_vscode.py", "--check"]),
		"调色步骤全关时产物与中间主题逐键相等(没有未登记的改色)": () => runUv(root, ["tools/gen_vscode.py", "--identity"], { COMFORT_STEPS: "none" }),
		// 只门禁清晰维度里有对应看不清类步骤的子指标(口径见 tools/metrics.py 的 CLEAR_GATE); 其余维度只作参考报告(npm run metrics)
		"配色清晰门禁达标 (终端 / 编辑区 / 界面的可读下限与选区可见)": () =>
			runUv(root, [
				"tools/metrics.py",
				"--check",
				...files("themes").filter(name => name.endsWith(".json")),
				// .terminal 要用 macOS 的 AppKit 解码, 其他平台(如 CI 的 Linux)只检 VS Code 主题
				...(process.platform === "darwin" ? files("terminal").filter(name => name.endsWith(".terminal")) : []),
			]),
	};
}
