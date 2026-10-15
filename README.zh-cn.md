# Editor Comfort Theme

[![VS Marketplace](https://vsmarketplacebadges.dev/version-short/HeavenSky.editor-comfort-theme.svg?label=VS%20Marketplace)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![Installs](https://vsmarketplacebadges.dev/installs-short/HeavenSky.editor-comfort-theme.svg)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE.txt)

[English](./README.md) · **简体中文**

> 市场页只渲染英文版 README, 不随访问者的显示语言切换; 插件描述会随 VS Code 显示语言切换为中文.

面向长时间编码的 16 套 VS Code 配色主题. 每一套都保留一款广受欢迎主题的配色(One Dark Pro, One Light, Ayu, Solarized, GitHub, Dracula, Night Owl, Monokai, One Monokai 与 Palenight), 只修看不清的地方, 看上去就是你熟悉的那套主题.

## 特性

- **原色优先**: 底色, 正文与语法色与原主题一致; 只有看不清的颜色才调整, 且只调到够用.
- **处处可读**: 正文, 语法色与终端色对比度不低于 4.5, 注释 3.4, 选区看得出, 徽标, 按钮与选中行上的字可读; 发布前门禁逐套检查.
- **覆盖完整**: VS Code 约两百个写死默认值的界面色(终端, diff, git 标记等)和原主题缺的语法规则, 都按本主题色板补齐, 不改原主题已定义的任何颜色.
- **零开销**: 纯静态主题文件, 无设置项, 无激活事件, 无运行时代码.
- **终端配套**: 每套主题都附同色板的 macOS Terminal.app 配置.

## 主题一览

| 主题 | 原主题 | 可读性修正 |
| --- | --- | --- |
| **C One Dark** | One Dark Pro 3.20.2 | 行号与焦点描边可读, 终端选区看得出 |
| **C One Light** | Atom One Light 2.3.0 | 注释 2.5 → 3.4, 偏淡的字符串, 类型与常量提到 4.5 |
| **C Ayu Dark** | ayu Mirage | 侧栏与活动栏文字可读 |
| **C Ayu Light** | ayu Light | 注释 2.2 → 3.4, 偏淡的字符串, 数字与终端色提到 4.5; 徽标与按钮上的字可读 |
| **C Sunlit Dark** | Solarized Dark | 注释 2.8 → 3.4, 语法色从约 3.3 提到 4.5, 终端选区看得出 |
| **C Sunlit Light** | Solarized Light | 正文 4.1 → 4.6, 注释 2.5 → 3.4, 语法色从约 3.0 提到 4.5, 编辑区与终端选区看得出 |
| **C GitHub Dark** | GitHub Dark Dimmed 6.3.5 | 几乎不变: 徽标字与查找高亮 |
| **C GitHub Light** | GitHub Light Default 6.3.5 | 几乎不变: 三个偏淡的终端色 |
| **C Dracula Dark** | Dracula Soft 2.25.1 | 几乎不变: 徽标字与输入框选区 |
| **C Dracula Light** | Dracula 官方浅色色板 Alucard | 全新浅色设计: Dracula Soft 的结构换上 Alucard 色板, 米色底 |
| **C Owl Dark** | Night Owl 2.1.1 | diff 新增色与查找高亮可读 |
| **C Owl Light** | Night Owl Light 2.1.1 | 注释 2.6 → 3.4, 偏淡的正则, 运算符与属性提到 4.5, 终端色可读 |
| **C Moka Dark** | One Monokai 0.5.2 | 注释 2.8 → 3.4 |
| **C Moka Light** | 经典 Monokai 色板 | 全新浅色设计: 以 Monokai 的正文色 `#F8F8F2` 作底, 底色 `#272822` 作正文, 彩色压深到浅底可读 |
| **C Pale Dark** | Palenight 2.0.5 | 注释 2.8 → 3.4, 侧栏与状态栏文字可读 |
| **C Pale Light** | Palenight 2.0.5 色相 | 全新浅色设计: 薰衣草色底, 偏紫的深靛正文, Palenight 彩色压深, 与 C Owl Light 明显区分 |

本来读得清的颜色原样保留: 不换底色, 不减淡正文, 不压彩色. 主题统一命名为 `C <Name> Dark` / `C <Name> Light`(`settings.json` 里的主题 ID 相同, 如 `"workbench.colorTheme": "C One Dark"`), 不与原主题重名.

通过 "首选项: 颜色主题"(`⌘K ⌘T` / `Ctrl+K Ctrl+T`)切换.

## 主题截图

在真实 VS Code 窗口里截取: 源代码管理, TypeScript, Python 与终端色板. 每张图下方的链接是 资源管理器 + Markdown + Less + 问题面板, 以及搜索视图(聚焦的搜索框) + 输出面板的截图.

| 深色 | 浅色 |
| --- | --- |
| **C One Dark**<br>![C One Dark](media/screenshots/one-dark-b.jpg)<br>[资源管理器与问题面板](media/screenshots/one-dark-a.jpg) · [搜索与输出面板](media/screenshots/one-dark-c.jpg) | **C One Light**<br>![C One Light](media/screenshots/one-light-b.jpg)<br>[资源管理器与问题面板](media/screenshots/one-light-a.jpg) · [搜索与输出面板](media/screenshots/one-light-c.jpg) |
| **C Ayu Dark**<br>![C Ayu Dark](media/screenshots/ayu-dark-b.jpg)<br>[资源管理器与问题面板](media/screenshots/ayu-dark-a.jpg) · [搜索与输出面板](media/screenshots/ayu-dark-c.jpg) | **C Ayu Light**<br>![C Ayu Light](media/screenshots/ayu-light-b.jpg)<br>[资源管理器与问题面板](media/screenshots/ayu-light-a.jpg) · [搜索与输出面板](media/screenshots/ayu-light-c.jpg) |
| **C Sunlit Dark**<br>![C Sunlit Dark](media/screenshots/sunlit-dark-b.jpg)<br>[资源管理器与问题面板](media/screenshots/sunlit-dark-a.jpg) · [搜索与输出面板](media/screenshots/sunlit-dark-c.jpg) | **C Sunlit Light**<br>![C Sunlit Light](media/screenshots/sunlit-light-b.jpg)<br>[资源管理器与问题面板](media/screenshots/sunlit-light-a.jpg) · [搜索与输出面板](media/screenshots/sunlit-light-c.jpg) |
| **C GitHub Dark**<br>![C GitHub Dark](media/screenshots/github-dark-b.jpg)<br>[资源管理器与问题面板](media/screenshots/github-dark-a.jpg) · [搜索与输出面板](media/screenshots/github-dark-c.jpg) | **C GitHub Light**<br>![C GitHub Light](media/screenshots/github-light-b.jpg)<br>[资源管理器与问题面板](media/screenshots/github-light-a.jpg) · [搜索与输出面板](media/screenshots/github-light-c.jpg) |
| **C Dracula Dark**<br>![C Dracula Dark](media/screenshots/dracula-dark-b.jpg)<br>[资源管理器与问题面板](media/screenshots/dracula-dark-a.jpg) · [搜索与输出面板](media/screenshots/dracula-dark-c.jpg) | **C Dracula Light**<br>![C Dracula Light](media/screenshots/dracula-light-b.jpg)<br>[资源管理器与问题面板](media/screenshots/dracula-light-a.jpg) · [搜索与输出面板](media/screenshots/dracula-light-c.jpg) |
| **C Owl Dark**<br>![C Owl Dark](media/screenshots/owl-dark-b.jpg)<br>[资源管理器与问题面板](media/screenshots/owl-dark-a.jpg) · [搜索与输出面板](media/screenshots/owl-dark-c.jpg) | **C Owl Light**<br>![C Owl Light](media/screenshots/owl-light-b.jpg)<br>[资源管理器与问题面板](media/screenshots/owl-light-a.jpg) · [搜索与输出面板](media/screenshots/owl-light-c.jpg) |
| **C Moka Dark**<br>![C Moka Dark](media/screenshots/moka-dark-b.jpg)<br>[资源管理器与问题面板](media/screenshots/moka-dark-a.jpg) · [搜索与输出面板](media/screenshots/moka-dark-c.jpg) | **C Moka Light**<br>![C Moka Light](media/screenshots/moka-light-b.jpg)<br>[资源管理器与问题面板](media/screenshots/moka-light-a.jpg) · [搜索与输出面板](media/screenshots/moka-light-c.jpg) |
| **C Pale Dark**<br>![C Pale Dark](media/screenshots/pale-dark-b.jpg)<br>[资源管理器与问题面板](media/screenshots/pale-dark-a.jpg) · [搜索与输出面板](media/screenshots/pale-dark-c.jpg) | **C Pale Light**<br>![C Pale Light](media/screenshots/pale-light-b.jpg)<br>[资源管理器与问题面板](media/screenshots/pale-light-a.jpg) · [搜索与输出面板](media/screenshots/pale-light-c.jpg) |

## 调校原则

每套主题分三步生成:

1. **原主题**: 原样取自发布版本(三套全新浅色设计先由对应的深色原主题生成).
2. **补全**: 只补缺失. VS Code 会写死默认值的界面色取本主题终端色的色相, 文字不比 VS Code 默认色难读(最多要求到对比度 4.5); 语法规则来自全部原主题合并的规则池, 只补原主题没上色的 scope; 会改掉原主题已上色 token 的规则(如外层已上色, 内层被补)经样例文件分词实测剔除.
3. **可读性修正**: 只改看不清的一侧, 只改到够用, 色相与饱和度不变: 正文, 语法色与终端色到对比度 4.5, 注释与终端暗灰到 3.4, 行号到 2.2, 非活动界面文字与焦点描边到 3.0; 编辑区, 输入框与终端选区看得出, 选区上的字可读; 徽标, 按钮与选中行上的字到 4.5, 字不换边.

压亮度, 去荧光, 压暗底色, 压饱和度等防刺眼与观感类调整仍保留在生成工具里, 默认关闭.

## 安装

- **VS Code**: 在扩展面板搜索 `Editor Comfort Theme`, 或在命令面板执行 `ext install HeavenSky.editor-comfort-theme`.
- **其他兼容 VS Code 的编辑器**: 从 [GitHub Release](https://github.com/HeavenSky/editor-comfort-theme/releases) 下载 `.vsix`, 执行 "扩展: 从 VSIX 安装…".

要求 VS Code `1.101.0` 及以上.

### Terminal.app 配置

每套主题在仓库的 [`terminal/`](./terminal/) 目录下都有同色板的 macOS Terminal.app 配置. 双击 `.terminal` 文件导入. 导入不会覆盖已有的同名配置, Terminal 会另建一份 `<名称> 1`, 所以先在 设置 → 描述文件 里删掉旧配置(或导入后再改名).

## 关闭斜体或粗体

主题是静态文件, 没有设置项; 在 `settings.json` 里覆盖字形即可:

```jsonc
"editor.tokenColorCustomizations": {
	"textMateRules": [
		{ "scope": ["comment", "variable.parameter"], "settings": { "fontStyle": "" } }
	]
}
```

## 许可

[MIT](./LICENSE.txt). 基于 One Dark Pro, One Light, ayu, VS Code 的 Solarized, GitHub, Dracula(含 Alucard 色板), Night Owl, One Monokai, Palenight 主题与经典 Monokai 色板, 均为 MIT, 见 [NOTICE.md](./NOTICE.md).
