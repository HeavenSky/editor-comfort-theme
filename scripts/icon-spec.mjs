/**
 * 插件图标前景: 编辑器窗口左深右浅(浅侧为柔和米色), 深侧月牙配三颗大小星星, 浅侧小太阳配三朵大小白云(星与云均为两层明暗), 底部一排柔和的主题色圆点, 表达"深浅多套护眼主题";
 * 淡紫窗口描边沿用 HeavenSky 系列插件图标, 其余用低饱和色, 整组居中。
 *
 * 底座 (画布尺寸, 圆角, 背景渐变, 描边) 来自 `lib/icon-brand.mjs`, 这里只描述前景。
 * SVG 与 PNG 都由 `scripts/gen-icon.mjs` 从这一份数据生成, 不要手写 `media/icon.svg`。
 */
import { SIZE, baseShapes } from "./lib/icon-brand.mjs";

const EDGE = "#C792EA";
// 月牙由同色圆在深色面上挖出; 深色面与挖空圆必须同色, 否则会留一圈暗边
const DARK = "#2E3446";
const LIGHT = "#E3DCCB";
const MOON = "#C9B6EC";
const SUN = "#E8B467";
const SUN_RAY = "#E2A85E";
// 星星与白云统一做两层明暗: 暗部下移作阴影, 亮部叠在上面
const STAR_SHADE = "#A893DA";
const STAR_LIGHT = "#DCCEFA";
const CLOUD_SHADE = "#D6CCBA";
const CLOUD_LIGHT = "#F8F4EC";
const THEME_COLORS = ["#E8919A", "#EEB07F", "#E9CF7E", "#A9CC94", "#86BEDC", "#B5A2E6"];

// 窗口取正方形并居中, 与图标外形一致
const WIN = { x: 32, y: 32, w: 192, h: 192, r: 34 };
const MID = WIN.x + WIN.w / 2;
const DOTS = { r: 8.5, step: 25, y: 190 };
const DOT_X0 = MID - ((THEME_COLORS.length - 1) * DOTS.step) / 2;
// 月亮与太阳在各自半边的水平中心, 垂直方向居中于窗口顶边到圆点行之间
const ROW_Y = (WIN.y + DOTS.y - DOTS.r) / 2 + 2;
const LEFT_X = WIN.x + WIN.w / 4;
const RIGHT_X = MID + WIN.w / 4;

const MOON_R = 31;
const CUT = { r: 26.5, dx: 13, dy: -9.5 };
// 月牙的视觉重心偏左下; 按包围盒中心与面积重心的折中做光学居中, 否则看起来偏左
const MOON_SHIFT = { x: 6, y: -4 };
const MOON_AT = { x: LEFT_X + MOON_SHIFT.x, y: ROW_Y + MOON_SHIFT.y };
const SUN_AT = { x: RIGHT_X, y: ROW_Y };

const circle = (cx, cy, r, fill) => ({ kind: "circle", cx, cy, r, fill });
const rect = (x, y, w, h, r, fill) => ({ kind: "roundedRect", x, y, w, h, r, fill });
const seg = (x1, y1, x2, y2, stroke, strokeWidth) => ({ kind: "polyline", points: [[x1, y1], [x2, y2]], stroke, strokeWidth });
// 五角星: 渲染器没有多边形填充, 用闭合的五角星轮廓加粗圆头描边, 小尺寸下呈实心且角是圆的
const star = (cx, cy, r, fill) => ({
	kind: "polyline",
	points: Array.from({ length: 11 }, (_, i) => {
		const a = -Math.PI / 2 + (i * Math.PI) / 5;
		const rr = i % 2 === 0 ? r : r * 0.45;
		return [cx + Math.cos(a) * rr, cy + Math.sin(a) * rr];
	}),
	stroke: fill,
	strokeWidth: r * 0.8,
});
// 以 (cx, cy) 为中心缩放圆与圆角矩形, 用来派生小一号的云
const scaleAt = (s, cx, cy, k) =>
	s.kind === "circle"
		? { cx: cx + (s.cx - cx) * k, cy: cy + (s.cy - cy) * k, r: s.r * k }
		: { x: cx + (s.x - cx) * k, y: cy + (s.y - cy) * k, w: s.w * k, h: s.h * k, r: s.r * k };
const cloud = (cx, cy, fill) => [
	circle(cx - 11, cy + 2, 9.5, fill),
	circle(cx + 1, cy - 4, 12, fill),
	circle(cx + 13, cy + 2, 8.5, fill),
	rect(cx - 20, cy + 1, 42, 11, 5.5, fill),
];
// 白云只作点缀, 按比例缩小, 不能和太阳抢主体; 暗部整体下移一点作阴影, 亮部在上
const smallCloud = (cx, cy, k) => [
	...cloud(cx, cy + 2, CLOUD_SHADE).map(s => ({ ...s, ...scaleAt(s, cx, cy + 2, k) })),
	...cloud(cx, cy, CLOUD_LIGHT).map(s => ({ ...s, ...scaleAt(s, cx, cy, k) })),
];
// 星星与白云同一做法: 同形暗部下移作阴影, 亮部在上
const shadedStar = (cx, cy, r) => [star(cx, cy + Math.max(1.2, r * 0.25), r, STAR_SHADE), star(cx, cy, r, STAR_LIGHT)];

export default {
	size: SIZE,
	label: "Editor Comfort Theme",
	shapes: [
		...baseShapes(),
		rect(WIN.x, WIN.y, WIN.w, WIN.h, WIN.r, DARK),
		// 右半浅色: 圆角矩形贴右边, 再用直角矩形补平中线处的圆角
		rect(MID, WIN.y, WIN.w / 2, WIN.h, WIN.r, LIGHT),
		rect(MID, WIN.y, WIN.r + 2, WIN.h, 0, LIGHT),
		{ kind: "roundedRectStroke", ...WIN, stroke: EDGE, strokeWidth: 10 },
		circle(MOON_AT.x, MOON_AT.y, MOON_R, MOON),
		circle(MOON_AT.x + CUT.dx, MOON_AT.y + CUT.dy, CUT.r, DARK),
		...shadedStar(LEFT_X + 30, ROW_Y - 32, 6),
		...shadedStar(LEFT_X + 33, ROW_Y + 26, 4.5),
		...shadedStar(LEFT_X - 30, ROW_Y + 33, 3.5),
		// 小太阳: 8 道圆头短光芒围绕圆心
		...Array.from({ length: 8 }, (_, i) => {
			const a = (i * Math.PI) / 4;
			return seg(SUN_AT.x + Math.cos(a) * 21, SUN_AT.y + Math.sin(a) * 21, SUN_AT.x + Math.cos(a) * 27, SUN_AT.y + Math.sin(a) * 27, SUN_RAY, 6);
		}),
		circle(SUN_AT.x, SUN_AT.y, 14, SUN),
		...smallCloud(SUN_AT.x + 22, ROW_Y + 34, 0.5),
		...smallCloud(SUN_AT.x - 28, ROW_Y - 30, 0.35),
		...smallCloud(SUN_AT.x - 28, ROW_Y + 33, 0.3),
		...THEME_COLORS.map((fill, i) => circle(DOT_X0 + i * DOTS.step, DOTS.y, DOTS.r, fill)),
	],
};
