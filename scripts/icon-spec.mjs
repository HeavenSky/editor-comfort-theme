/**
 * 插件图标前景: 上排淡紫月牙与暖黄太阳并列, 表达"深浅两类主题";
 * 下排一行六色主题色点, 表达"编辑器配色"。
 * 画法与配色对齐 HeavenSky 系列插件图标: 深色底座上直接放扁平圆头图形, 前景色取自系列的同一组强调色。
 *
 * 底座 (画布尺寸, 圆角, 背景渐变, 描边) 来自 `lib/icon-brand.mjs`, 这里只描述前景。
 * SVG 与 PNG 都由 `scripts/gen-icon.mjs` 从这一份数据生成, 不要手写 `media/icon.svg`。
 */
import { BACKGROUND_FROM, BACKGROUND_TO, SIZE, baseShapes } from "./lib/icon-brand.mjs";

const PURPLE = "#C792EA";
const YELLOW = "#FFC145";
const DOT_COLORS = ["#FF6B60", "#FF9E64", "#FFC145", "#4EDD6E", "#6FD6FF", "#C792EA"];

const MID = SIZE / 2;
// 上排月亮与太阳关于画布中线对称; 整组 (上排顶到色点底) 在画布内上下居中
const TOP_Y = 103.5;
const COL_DX = 46;

// 月牙按包围盒对齐列中心: 实测包围盒中心在圆心左侧约 0.9px 处, 因此圆心右移补回
const MOON = { cx: MID - COL_DX + 0.9, cy: TOP_Y, r: 39 };
// 挖空圆偏右上, 留下朝左下张开的月牙
const CUT = { cx: MOON.cx + 0.45 * MOON.r, cy: TOP_Y - 0.35 * MOON.r, r: 0.825 * MOON.r };
const SUN = { cx: MID + COL_DX, cy: TOP_Y, core: 17, rayFrom: 26, rayTo: 35, rayWidth: 8 };

const DOTS = { y: 181.5, r: 10, step: 28 };

const circle = (cx, cy, r, fill) => ({ kind: "circle", cx, cy, r, fill });
const seg = (x1, y1, x2, y2, stroke, strokeWidth) => ({ kind: "polyline", points: [[x1, y1], [x2, y2]], stroke, strokeWidth });

// 底座在 (x, y) 处的颜色: 对角渐变的取色只与 x + y 线性相关
const backgroundAt = (x, y) => {
	const [from, to] = [BACKGROUND_FROM, BACKGROUND_TO].map(hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)));
	const t = (x + y) / (2 * SIZE);
	return `#${from.map((c, i) => Math.round(c + (to[i] - c) * t).toString(16).padStart(2, "0")).join("")}`;
};
// 渲染器没有布尔运算, 月牙用"整圆 + 挖空圆"叠出; 底座是渐变, 挖空圆不能用纯色,
// 改用同向对角渐变, 起止色取底座在挖空圆包围盒两角的颜色, 与底座逐点重合, 两圆边缘都是真圆
const holeCircle = (cx, cy, r) =>
	circle(cx, cy, r, {
		kind: "linear",
		from: backgroundAt(cx - r, cy - r),
		to: backgroundAt(cx + r, cy + r),
		direction: "diagonal",
	});

export default {
	size: SIZE,
	label: "Editor Comfort Theme",
	shapes: [
		...baseShapes(),
		circle(MOON.cx, MOON.cy, MOON.r, PURPLE),
		holeCircle(CUT.cx, CUT.cy, CUT.r),
		...Array.from({ length: 8 }, (_, i) => {
			const a = (i * Math.PI) / 4;
			const { cx, cy, rayFrom, rayTo, rayWidth } = SUN;
			return seg(cx + Math.cos(a) * rayFrom, cy + Math.sin(a) * rayFrom, cx + Math.cos(a) * rayTo, cy + Math.sin(a) * rayTo, YELLOW, rayWidth);
		}),
		circle(SUN.cx, SUN.cy, SUN.core, YELLOW),
		...DOT_COLORS.map((fill, i) => circle(MID + (i - (DOT_COLORS.length - 1) / 2) * DOTS.step, DOTS.y, DOTS.r, fill)),
	],
};
