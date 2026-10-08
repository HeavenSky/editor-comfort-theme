// @ts-check
// 主题配色测试文件: 在 VS Code 里打开本文件, 用 "首选项: 颜色主题" 逐个切换, 对照下面各段的着色.
// 覆盖: 关键字 / 字符串 / 数字 / 正则 / 函数 / 类型 / 参数 / 属性 / 注释与 JSDoc / 括号配对多层 / 诊断波浪线 /
//       弃用删除线 / 未使用变量淡化 / 模板字符串插值 / 中文混排; JSX 在同目录的 theme-preview.jsx. 本目录不进插件包.

import { readFile } from 'node:fs/promises';
import * as path from 'node:path';
import defaultExport, { named as alias } from './not-exist.js'; // 不存在的模块: 观察导入报错的波浪线

/* 块注释: TODO FIXME NOTE 这类标记的高亮取决于是否装了相关插件 */

/**
 * JSDoc: 标签, 类型与参数名各自着色.
 * @template T
 * @param {string} name 名称参数
 * @param {{ retries?: number, signal?: AbortSignal }} [options] 可选配置
 * @returns {Promise<T | null>} 结果或空
 * @see https://code.visualstudio.com/api/references/theme-color 链接色
 */
export async function loadConfig(name, options = {}) {
	const { retries = 3, signal } = options;
	for (let attempt = 0; attempt < retries; attempt++) {
		if (signal?.aborted) return null;
		try {
			const text = await readFile(path.join(process.cwd(), `${name}.json`), 'utf8');
			return JSON.parse(text);
		} catch (error) {
			console.warn(`第 ${attempt + 1} 次读取失败:`, error instanceof Error ? error.message : error);
		} finally {
			debugger;
		}
	}
	throw new TypeError('配置读取失败: ' + name);
}

// ---- 字面量: 数字的各种写法, 字符串转义, 正则, 内置常量 ----
const numbers = [42, 3.14159, -0.5e-10, 0xff_ff, 0o755, 0b1010_1010, 1_000_000n, NaN, Infinity];
const strings = ['单引号', "双引号 \"转义\" \t \n \u4e2d \x41", `模板 ${numbers.length} 个 ${strings2()}`];
const regex = /^(?<year>\d{4})-(?<month>0[1-9]|1[0-2])-\d{2}$/giu;
const flags = { yes: true, no: false, nothing: null, missing: undefined, big: Number.MAX_SAFE_INTEGER, pi: Math.PI };

function strings2() {
	return String.raw`C:\path\${'不插值'}` + '\u{1F3A8}';
}

// ---- 类: 继承, 私有字段, 静态块, getter / setter, super / this, new.target ----
class Shape {
	static #count = 0;
	static {
		Shape.#count = 0;
	}
	#name;

	/** @param {string} name */
	constructor(name) {
		if (new.target === Shape) throw new Error('抽象类');
		this.#name = name;
		Shape.#count++;
	}

	get name() {
		return this.#name;
	}

	set name(value) {
		this.#name = value.trim();
	}

	/** @returns {number} */
	area() {
		return 0;
	}

	static get count() {
		return Shape.#count;
	}
}

export class Circle extends Shape {
	/** @param {number} radius */
	constructor(radius) {
		super('circle');
		this.radius = radius;
	}

	/** @override */
	area() {
		return Math.PI * this.radius ** 2;
	}

	/** @deprecated 请改用 area(); 调用处应显示删除线 */
	legacyArea() {
		return this.area();
	}
}

// ---- 括号配对着色: 圆括号, 方括号, 花括号多层嵌套, 观察颜色是否按层轮换且不刺眼 ----
const nested = { a: [{ b: (1 + (2 * (3 - [4, 5][0]))) }], c: [[[{ d: { e: [6] } }]]] };

// ---- 运算符, 解构, 展开, 可选链, 空值合并, 箭头函数, 生成器, 标签 ----
const sum = (/** @type {number[]} */ ...values) => values.reduce((total, value) => total + value, 0);
const { a: [{ b }], ...rest } = nested;
const label = rest.c?.[0]?.[0]?.[0]?.d?.e ?? '默认值';
let counter = 0;
counter += b > 10 && b !== 0 ? b % 3 : ~b >>> 1;
counter ||= 1;

function* idGenerator(prefix = 'id') {
	let index = 0;
	outer: while (true) {
		for (const char of prefix) {
			if (char === '-') continue outer;
			yield `${prefix}-${index++}`;
		}
	}
}

switch (Array.isArray(label) ? label.length : -1) {
	case 1:
		void label;
		break;
	default:
		console.log(label, sum(1, 2, 3), idGenerator().next().value);
}

// ---- 诊断: 以下各行是故意写的, 用来观察 错误 / 警告 / 弃用 / 未使用 的显示 ----
/** @type {number} */
const typed = '不是数字'; // 类型错误: 红色波浪线
new Circle(2).legacyArea(); // 弃用: 删除线
const unusedVariable = 1; // 未使用: 变量名淡化显示
undefinedFunction(); // 未定义: 红色波浪线

export default { loadConfig, Circle, numbers, strings, regex, flags, defaultExport, alias, typed, counter };
