# Editor Comfort Theme

[![VS Marketplace](https://vsmarketplacebadges.dev/version-short/HeavenSky.editor-comfort-theme.svg?label=VS%20Marketplace)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![Installs](https://vsmarketplacebadges.dev/installs-short/HeavenSky.editor-comfort-theme.svg)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE.txt)

[English](./README.md) · **简体中文**

> 市场页只渲染英文版 README, 不随访问者的显示语言切换; 插件描述会随 VS Code 显示语言切换为中文.

面向长时间编码的 13 套 VS Code 配色主题, 每一套都经过舒适度调整与适配. 配色设计参考广受欢迎的 One Dark Pro, One Light, Ayu, Solarized, GitHub, Dracula, Night Owl, One Monokai 与 Palenight 主题, 上手即熟悉.

## 特性

- **全部舒适度适配**: 13 套主题都按长时间使用做了适配, 并全部通过同一套门禁: WCAG 对比度, OKLCH 彩度, 以及柔和与防疲劳打分.
- **熟悉的配色**: 配色参考官方主题, 保留色相, 调校明度与彩度.
- **覆盖完整**: VS Code 约两百个写死默认值的界面色(括号对, 终端, diff 等)全部按本主题色板补齐.
- **零开销**: 纯静态主题文件, 无设置项, 无激活事件, 无运行时代码.
- **终端配套**: 每套主题都附同色板的 macOS Terminal.app 配置.

## 主题一览

| 主题 | 配色参考 | 舒适度调整 |
| --- | --- | --- |
| **Comfort One Dark** | One Dark Pro 3.20.2 | 保留 One Dark Pro 的底色, 正文, italic, bold 与偏橙的终端黄; 彩色更柔和, 注释更易读 |
| **Comfort One Light** | Atom One Light 2.3.0 | 底色压暗(`#FAFAFA` → `#EDEDEF`), 正文减淡, 彩色更柔和 |
| **Comfort Ayu Dark** | ayu Mirage | 正文减淡, 字符串不再刺眼, 半透明标点改为清楚可读 |
| **Comfort Ayu Light** | ayu Light | 底色压暗, 正文加深 |
| **Comfort Sunlit Dark** | Solarized Dark | 正文提亮, 彩色更柔和 |
| **Comfort Sunlit Light** | Solarized Light | 底色压暗, 正文加深 |
| **Comfort GitHub Dark** | GitHub Dark Dimmed 6.3.5 | 正文与彩色略减淡, 保留灰蓝底色 |
| **Comfort GitHub Light** | GitHub Light Default 6.3.5 | 纯白底压暗, 正文对比度从 15.8 减到 8.0 |
| **Comfort Dracula Dark** | Dracula Soft 2.25.1 | 正文对比度从 13.2 减到 7.0, 彩色更柔和 |
| **Comfort Owl Dark** | Night Owl 2.1.1 | 近纯黑底抬亮(保留深蓝色相), 正文对比度从 13.5 减到 7.0 |
| **Comfort Owl Light** | Night Owl Light 2.1.1 | 近纯白底压暗, 注释明显更易读 |
| **Comfort Moka Dark** | One Monokai 0.5.2 | One Dark 底色上的 Monokai 彩色更柔和 |
| **Comfort Pale Dark** | Palenight 2.0.5 | 正文与彩色减淡 |

全部主题通过同一套门禁: 正文, 注释与行号的对比度落在舒适区间, 彩色与界面文字(侧边栏, 文件树, 标签页, 活动栏)不比正文更抢眼, 面板底色接近中性, 徽标安静, 高亮不刺眼. 主题统一命名为 `Comfort <Name> Dark` / `Comfort <Name> Light`.

通过 "首选项: 颜色主题"(`⌘K ⌘T` / `Ctrl+K Ctrl+T`)切换.

## 调校原则

全部主题逐色按三个目标调校:

- **清晰**: 正文, 语法色, 行号与终端色相对各自底色达到 WCAG 对比度下限.
- **安静**: 注释在所有主题中统一为对比度 3.2; 深色主题的语法色对比度不超过正文的 1.1 倍.
- **护眼**: 彩色封顶彩度; 深色底避开纯黑, 浅色底避开纯白.

## 安装

- **VS Code**: 在扩展面板搜索 `Editor Comfort Theme`, 或在命令面板执行 `ext install HeavenSky.editor-comfort-theme`.
- **其他兼容 VS Code 的编辑器**: 从 [GitHub Release](https://github.com/HeavenSky/editor-comfort-theme/releases) 下载 `.vsix`, 执行 "扩展: 从 VSIX 安装…".

要求 VS Code `1.101.0` 及以上.

### Terminal.app 配置

每套主题在仓库的 [`terminal/`](./terminal/) 目录下都有同色板的 macOS Terminal.app 配置. 双击 `.terminal` 文件导入, 同名配置会被覆盖; 运行 `bash terminal/terminal-preview.sh --full` 可显示 16 色矩阵.

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

### 改配色

`themes/*.json` 与 `terminal/*.terminal` 都是生成物, 不要手改, 下次生成会被覆盖, `npm run check` 也会报漂移. 生成的输入:

- `tools/themes.py`: 每套主题的目标底色, 前景, 16 色终端与调色参数(彩度上限, 语法色与注释色的对比度下限).
- `tools/sources/*.json`: 原主题模板. 全部主题保留其全部界面键与语法规则, 只逐色变换.
- `tools/sources/vscode-color-registry.json`: VS Code 颜色注册表, 含核心颜色, 终端 16 色与内置扩展声明的颜色, 逐键记录默认值, 是否须半透明, 是否已废弃. 默认值写死的键, 原主题没定义的一律按本主题色板补齐; VS Code 升级后用 `npm run extract:registry` 重新提取.
- 每套生成的主题都按 `vscode://schemas/color-theme` 校验(`tools/schema.py`): 未注册或已废弃的颜色键丢弃(有官方替代键的改名), 须半透明的颜色换算成等效的半透明值, VS Code 不生效的 token 规则字段(token 背景色, `fontStyle: normal` 等)删除或改成等效写法. 任意主题可用 `uv run tools/schema.py <文件>...` 校验.
- 语法规则来自同一个规则池(`tools/pool.py`): 全部原主题的 token 选择器(约 1300 个)合并成池子, 每个选择器裁决出一个角色(关键字, 函数, 类型, 属性, 字符串等), 每套主题都用自己的角色色为整个池子着色, 覆盖面一致且丰富, 包括各语言专属的规则. 角色按 TextMate 命名约定且原主题不反对时自动确定; 标点与 `meta.*` 包裹 scope 跟随外层; 其余未标注前用推荐值, 人工标注存于 `tools/sources/pool-overrides.json`. 原主题有意弱化的选择器(标点, 文档字符串, 注释里的内容等)用本角色色的暗淡版本, 不加粗; 调色把同一主题里两个本不同色的角色挤到一起时, 再按明度(必要时稍转色相)拉开. 普通变量在每套主题里有一个派生专用色: 彩度约 0.085, 明度贴近参数色, 色相取离本主题其他语法色最远的方向, 因为任何现成的角色色都会与某个角色撞色. `uv run tools/pool.py` 查看各层数量, `uv run tools/pool.py --annotate <out.html>` 生成带颜色预览, 键盘操作的标注页.
- 语法着色统一覆盖(`tools/coverage.py`): 每套主题都为同样的 33 个常用 scope 着色(类型, 命名空间, 变量, 参数, 属性, 对象键, Markdown 标题, 粗体, 斜体, 引用, 链接等); 原主题没定义的, 取本主题最相近角色的颜色补上. 标点刻意不纳入: 引号与注释符号套在字符串和注释里, 应保持字符串色与注释色.

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
uv run tools/metrics.py --strict --check <文件>...  # 另要求 柔和 与 防疲劳 两项通过
uv run tools/metrics.py --detail <文件>...  # 逐主题列出 柔和 / 防疲劳 的子指标与得分
```

- 对比度一律是 WCAG 对比度; 彩度是 OKLCH 的 C; 底亮度是 WCAG 相对亮度(0 纯黑, 1 纯白).
- 清晰分 高 / 中高 / 中, 护眼分 好 / 中; 达标 = 清晰 >= 中高, 护眼 = 好, 且 VS Code 主题覆盖了注册表里全部未废弃的写死默认色的键("未覆盖" 为 0), 没有 schema 问题("规范" 为 0), 并且常用 scope 全部着色("着色" 为 0). 打分只计 VS Code 实际生效的颜色.
- VS Code 主题另有两条上限, 超出即判清晰为中: 注释对比度不超过 4.2; 深色主题最亮的语法色不超过正文对比度的 1.1 倍. 行号对比度下限 2.0; 深色主题评"高"要求正文对比度在 7.0~8.5 之间.
- **柔和** 与 **防疲劳** 两项按 0~100 打分(规则见 `tools/comfort.py`): 每个子指标落在理想区间得 100, 到限值降到 60, 越过限值判不通过.
  - 柔和: 语法色平均彩度, 最大彩度, 彩色语法色的亮度跨度, 最亮语法色与正文之比, 面板底色彩度.
  - 防疲劳: 正文对比度, 注释对比度, 正文与注释的落差, 行号对比度, 底亮度, 面板亮块(大面积底色, 含列表选中行, 与编辑区底对比度超过 1.6), 高亮底色(刺眼或压字难读), 比正文更刺眼的界面文字与图标(侧边栏, 文件树, 扩展列表, 标签页标题, 活动栏), 以及抢眼(与编辑区底对比度超过 2.2, 深色与浅色主题同样适用)或字难读(低于 3.5)的徽标.
  - `--strict` 时判定; `npm run metrics` 与 `npm run check` 默认带 `--strict`, 全部主题须通过.
- 各项阈值见 `tools/metrics.py` 顶部常量; `tools/colorlib.py` 的 `tune` 是调色手段: 彩度封顶 + 明度推到对比度下限, 色相不动.
- "默认文字色配彩色背景"(如只写 `\e[41m`)在任何调色板下都看不清, 不计入指标; Terminal.app 的 dim 字按固定比例减淡且不可配置.

### 配色接近度

`tools/similar.py` 逐项比对 VS Code 颜色主题(CIEDE2000 色差), 找出整体接近, 只有少数几处差别大的主题对, 把差别大的地方按颜色对归成差异组; 选定差异组后可生成合并预览并跑一遍门禁:

```bash
npm run similar                                              # 全部主题两两比对
uv run tools/similar.py a.json b.json --merge out.json --take 1,3   # 以 a 为底, 差异组 1, 3 取 b 的颜色
```

### 发布前

```bash
npm run check       # 图标, 清单, 骨架漂移, 主题生成物漂移, 配色达标
npm run typecheck
npm test
npm run package     # 生成 artifacts/editor-comfort-theme-<版本>.vsix 并断言包内容
```

使用 npm 12 时, `npm ci` 只接受从 `registry.npmjs.org` 解析的 lockfile, 且依赖的安装脚本(`esbuild`, `@vscode/vsce-sign`, `fsevents`)默认不执行. 检查, 测试与打包都不需要它们; 只有本地签名或发布报错时, 才用 `npm install-scripts approve <包>` 放行. CI 使用 `.nvmrc` 指定的 Node 版本自带的 npm, 不受影响.

本仓库派生自 vsc-ext 工程骨架; 共享的骨架文件如有偏离, `npm run check` 会报出来.

## 许可

[MIT](./LICENSE.txt). 基于 One Dark Pro, One Light, ayu 与 VS Code 的 Solarized 主题, 均为 MIT, 见 [NOTICE.md](./NOTICE.md).
