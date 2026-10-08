// 主题配色测试文件(JSX 部分): 标签名, 组件名, 属性名, 属性值, 插值, 实体; 与 theme-preview.js 配合使用.
// 不开类型检查, 避免缺少 React 类型声明的报错盖住配色本身.
import { useState } from 'react';

export function View({ title = '主题预览' }) {
	const [count, setCount] = useState(0);
	return (
		<section className="card" data-count={count} aria-label={title}>
			<h1 style={{ color: 'var(--accent)', fontWeight: 600 }}>
				{title}: {count}
			</h1>
			{[1, 2, 3].map((item) => (
				<Item key={item} value={item} disabled={item === count} onPick={setCount} />
			))}
			<p>
				普通文本 &amp; 实体 &lt;tag&gt; {/* JSX 注释 */}
			</p>
		</section>
	);
}

function Item({ value, disabled, onPick }) {
	return (
		<button type="button" disabled={disabled} onClick={() => onPick(value)}>
			{value}
		</button>
	);
}
