# Editor Comfort Theme

[English](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/README.md) · **简体中文**

> 市场页只展示英文 README, 不随显示语言切换; 本页是中文版.

面向长时间编码的 7 套 VS Code 配色主题, 每一套都经过舒适度调整与适配. 配色设计参考官方的 One Dark Pro, One Light, Ayu 与 Solarized 主题, 上手即熟悉.

## 特性

- 全部舒适度适配: 7 套主题都按长时间使用做了适配, 并全部通过同一套 WCAG 对比度与 OKLCH 彩度门禁.
- 熟悉的配色: 配色参考官方主题, 保留色相, 调校明度与彩度.
- 覆盖完整: VS Code 约两百个写死默认值的界面色(括号对, 终端, diff 等)全部按本主题色板补齐.
- 零开销: 纯静态主题文件, 无设置项, 无激活事件, 无运行时代码.
- 终端配套: 6 套 Comfort 主题均附同色板的 macOS Terminal.app 配置.

## 主题一览

| 主题 | 配色参考 | 舒适度调整 |
| --- | --- | --- |
| **One Dark Pro Lite** | One Dark Pro 3.20.2 | 最接近原版: 正文不变, 在门禁内保留更多原版彩度, 启用 italic 与 bold |
| **Comfort One Dark** | One Dark Pro | 彩色更柔和, 正文略提亮 |
| **Comfort One Light** | Atom One Light | 底色压暗, 彩色更柔和 |
| **Comfort Ayu Dark** | ayu Mirage | 彩色更柔和, 字符串不再刺眼, 半透明标点改为清楚可读 |
| **Comfort Ayu Light** | ayu Light | 底色压暗, 正文加深 |
| **Comfort Solarized Dark** | Solarized Dark | 正文提亮, 彩色更柔和 |
| **Comfort Solarized Light** | Solarized Light | 底色压暗, 正文加深 |

通过 "首选项: 颜色主题"(`⌘K ⌘T` / `Ctrl+K Ctrl+T`)切换.

## 调校原则

全部主题逐色按三个目标调校:

- 清晰: 正文, 语法色, 行号与终端色相对各自底色达到 WCAG 对比度下限.
- 安静: 注释在所有主题中统一为对比度 3.2; 深色主题的语法色对比度不超过正文的 1.1 倍.
- 护眼: 彩色封顶彩度; 深色底避开纯黑, 浅色底避开纯白.

## 安装

- VS Code: 在扩展面板搜索 `Editor Comfort Theme`, 或在命令面板执行 `ext install HeavenSky.editor-comfort-theme`.
- 其他兼容 VS Code 的编辑器: 从 [GitHub Release](https://github.com/HeavenSky/editor-comfort-theme/releases) 下载 `.vsix`, 执行 "扩展: 从 VSIX 安装…".

要求 VS Code `1.101.0` 及以上.

### Terminal.app 配置

6 套 Comfort 主题在仓库的 `terminal/` 目录下有同色板的 macOS Terminal.app 配置, 双击 `.terminal` 导入(同名配置会被覆盖); `bash terminal/terminal-preview.sh --full` 显示 16 色矩阵.

## 关闭斜体或粗体

主题是静态文件, 没有设置项; 在 `settings.json` 里覆盖字形即可:

```jsonc
"editor.tokenColorCustomizations": {
	"textMateRules": [
		{ "scope": ["comment", "variable.parameter"], "settings": { "fontStyle": "" } }
	]
}
```

## 开发

### 看配色

用 VS Code 打开本仓库按 F5, 在调试窗口里打开 `samples/theme-preview.js` 与 `samples/theme-preview.jsx`, 用 "首选项: 颜色主题" 逐个切换. `.js` 里有故意写的类型错误, 弃用调用与未使用变量, 用来看诊断与淡化效果; `.jsx` 不开类型检查, 只看 JSX 着色.

### 改配色

`themes/*.json` 与 `terminal/*.terminal` 都是生成物, 不要手改, 下次生成会被覆盖, `npm run check` 也会报漂移. 生成的输入:

- `tools/themes.py`: 每套主题的目标底色, 前景, 16 色终端与调色参数(彩度上限, 语法色与注释色的对比度下限).
- `tools/sources/*.json`: 原主题模板. Comfort 主题保留其全部界面键与语法规则, 只逐色变换.
- `tools/sources/vscode-color-registry.json`: VS Code 颜色注册表. 默认值写死的键, 原主题没定义的一律按本主题色板补齐; VS Code 升级后用 `npm run extract:registry` 重新提取.

```bash
npm run extract:registry              # 从 /Applications/Visual Studio Code.app 提取颜色注册表
uv run tools/gen_vscode.py            # 生成 themes/*.json
uv run tools/gen_terminal.py          # 生成 terminal/*.terminal (仅 macOS), 可加 --font <PostScript 名> --size <字号>
npm run metrics                       # 指标表 + 达标判定, 不达标退出码 1
```

### 指标与达标口径

`tools/metrics.py` 可独立使用, 接受任意 `.terminal` 或 VS Code 颜色主题 `.json`(包括别人的主题):

```bash
uv run tools/metrics.py <文件>...           # 只输出指标表
uv run tools/metrics.py --check <文件>...   # 再按口径判定, 用作门禁
```

- 对比度一律是 WCAG 对比度; 彩度是 OKLCH 的 C; 底亮度是 WCAG 相对亮度(0 纯黑, 1 纯白).
- 清晰分 高 / 中高 / 中, 护眼分 好 / 中; 达标 = 清晰 >= 中高, 护眼 = 好, 且 VS Code 主题覆盖了注册表里全部写死默认色的键("未覆盖" 为 0).
- VS Code 主题另有两条上限, 超出即判清晰为中: 注释对比度不超过 3.5; 深色主题最亮的语法色不超过正文对比度的 1.1 倍.
- 各项阈值见 `tools/metrics.py` 顶部常量; `tools/colorlib.py` 的 `tune` 是调色手段: 彩度封顶 + 明度推到对比度下限, 色相不动.
- "默认文字色配彩色背景"(如只写 `\e[41m`)在任何调色板下都看不清, 不计入指标; Terminal.app 的 dim 字按固定比例减淡且不可配置.

### 发布前

```bash
npm run check       # 图标, 清单, 骨架漂移, 主题生成物漂移, 配色达标
npm run typecheck
npm test
npm run package     # 生成 artifacts/editor-comfort-theme-<版本>.vsix 并断言包内容
```

本仓库派生自 vsc-ext 工程骨架; 因为没有运行时代码, 有几份骨架文件做了受控偏离, 原因写在 `.template-shared` 的 `!` 行里.

## 许可

[MIT](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/LICENSE.txt). 基于 One Dark Pro, One Light, ayu 与 VS Code 的 Solarized 主题, 均为 MIT, 见 [NOTICE.md](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/NOTICE.md).
