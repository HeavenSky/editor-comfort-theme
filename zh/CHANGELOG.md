# 更新日志

[English](../CHANGELOG.md) · **简体中文**

## v0.0.5 2026-10-22

### 变更

- **本该区分的两类代码不再共用一种颜色。** 两类语法角色撞色时，其中一类改用本主题里的另一种颜色，先改常量、内置函数、参数这类次要角色。C Owl Light 的字符串改为金色；C Owl Dark 的类型改为黄色，暖桃色的字符串不变（[怎样区分](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/zh/docs/how-themes-are-tuned.md#让不同类的代码分得开)）。
- 彩色徽标、按钮和状态栏上的字必须由浅转深（或反过来）时，改用本主题的编辑区底色或正文色，不再用中性灰，读起来更清楚：C Dracula Dark 粉色徽标上的字变为 `#282A36`（对比度 6.1，原为 3.1）（[详见](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/zh/docs/how-themes-are-tuned.md#只修看不清的地方)）。
- Terminal.app 配置只设颜色、字体、光标和 120 × 30 的窗口，标题栏不再显示配置名和窗口尺寸。按键和 shell 退出后的行为沿用 Terminal.app 的默认值，Option 键不再当作 Meta 键；想保留的话，在“终端 → 设置 → 描述文件 → 键盘”里勾选“将 Option 键用作 Meta 键”。重新导入配置后生效（[导入配置](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/zh/docs/terminal-app.md#导入配置)）。

### 修复

- C One Light 的终端黄不再和终端绿是同一种绿色：改用 One Light 自己的金棕色 `#986801`，git 已修改标记和类图标也随之一致。

## v0.0.4 2026-10-16

### 破坏性变更

- 主题从 `Comfort <Name> Dark` / `Comfort <Name> Light` 改名为 `C <Name> Dark` / `C <Name> Light`（例如 `C One Dark`），主题选择器里的名称和设置里的 ID 都改了。VS Code 认不出旧名称，更新后请重新选择主题（或在 `settings.json` 里把 `workbench.colorTheme`、`workbench.preferredDarkColorTheme` 和 `workbench.preferredLightColorTheme` 改成新名称）。

### 变更

- **回到原主题的配色。** v0.0.3 重调了每一种颜色；现在每套主题保留原来的底色、正文、语法、终端和界面颜色，只改看不清的地方，也只改到够用（[调整了什么](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/zh/docs/how-themes-are-tuned.md#只修看不清的地方)）。
- 缺失的界面色和语法规则用各主题自己的色板补齐，不改原主题设过的任何颜色；浅色主题里 git 已修改标记因此不再是淡黄色（[怎样补全](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/zh/docs/how-themes-are-tuned.md#只补缺失)）。
- 深色主题里接近纯白的文字、图标、语法色和终端白压到 OKLCH 明度 0.88，色相不变；C Dracula Dark 的正文从 `#F6F6F4` 变为 `#D7D7D6`。
- 每套主题的终端选区都清楚可见：现在每套主题都设置了 `terminal.selectionBackground` 和 `terminal.inactiveSelectionBackground`（Terminal.app 配置的选区颜色也一样），不再退回很淡的编辑区选区色。正文本来就只是勉强可读的主题（C Sunlit）里，选区在保证上面文字对比度 3.5 的前提下尽量醒目。
- 文件名更短：`themes/one-dark.json` 取代 `themes/comfort-one-dark-color-theme.json`，截图同理。Terminal.app 配置移到 `assets/terminal/`（例如 `assets/terminal/one-dark.terminal`），导入后名为 `C One Dark` 等；请在 Terminal.app 里删掉旧的 `Comfort` 配置（[导入配置](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/zh/docs/terminal-app.md#导入配置)）。

- 文档：README 改为简短的概览；主题列表、截图、Terminal.app 配置、自定义和调色规则在[文档](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/zh/docs/README.md)下各有一页；中文页面统一放在 `zh/` 下。

### 修复

- VS Code 自动补上的状态色（例如 C Dracula 的信息色）不再和警告色重复。

## v0.0.3 2026-10-12

### 破坏性变更

- 主题名简化为 `Comfort <Name> Dark` / `Comfort <Name> Light`：One Dark Fit → **Comfort One Dark**，One Light Fit → **Comfort One Light**。主题文件和 Terminal.app 配置也按同样的 `comfort-<name>-dark|light` 命名，名称用一个单词的简称；Comfort Solarized Dark / Light 改名为 **Comfort Sunlit Dark / Light**。请重新选择主题，并重新导入 `.terminal` 文件。

### 新增

- 新增七套主题，从原主题自动改编，并按同一道门槛调校：**Comfort GitHub Dark**（源自 GitHub Dark Dimmed）、**Comfort GitHub Light**、**Comfort Dracula Dark**（源自 Dracula Soft）、**Comfort Owl Dark**（源自 Night Owl）、**Comfort Owl Light**（源自 Night Owl Light）、**Comfort Moka Dark**（源自 One Monokai）和 **Comfort Pale Dark**（源自 Palenight）。
- 新设计三套浅色主题，由 `tools/design.py` 从深色原主题生成，并按同一道门槛调校：**Comfort Dracula Light**（Dracula 官方的 Alucard 色板）、**Comfort Pale Light**（Palenight 的色相配淡薰衣草色底）和 **Comfort Moka Light**（经典 Monokai 色板，以它的文字色 `#F8F8F2` 作底色，与 Comfort Moka Dark 成对）。
- 为 Comfort One Dark 和 Comfort One Light 补上 Terminal.app 配置，现在每套主题都有。
- README 加入每套主题的截图（源代码管理、代码与终端颜色；资源管理器与问题面板；搜索与输出面板）。

### 变更

- 界面文字和图标不再比正文刺眼：侧栏、文件树、插件列表、标签页标题、活动栏图标和文件树的 git 颜色，以前在深色主题里接近纯白（对比度最高到正文的两倍），在浅色主题里接近纯黑。深色主题的徽标从亮色块改为较暗的彩色圆点，上面的字用正文色。
- 所有主题重新调色，观感更柔和，看久了不累：强调色饱和度降低；注释更亮，并与正文对比度挂钩；行号更暗；正文对比度不超过 7.5（深色）或 8.0（浅色）；浅色底色压暗到亮度最高 0.80（面板、输入框和小部件都不超过 0.85）；面板接近中性色，高亮不再刺眼。部分面板里原本会闪出刺眼的校验、合并和拖放背景色，这个问题也已修复。
- **Comfort One Light** 改用更暗的 `#E7E7E9` 底色。
- 筛选框和下拉框（问题面板、输出面板、设置）不再抢眼：描边接近中性色，对比度最高 2.0（Comfort Owl Dark 原来是 3.7，Comfort Pale Light 是 5.1）；占位文字为灰色，比输入的文字更淡（对比度 2.8–4.2；Comfort Pale Light 的占位文字原来比输入文字还亮）；输入的文字至少 4.5；焦点描边介于对比度 3.0 和正文的 0.8 倍之间。获得焦点的输入框不再比没有焦点的显得更暗（Comfort Owl 和 Pale 的焦点描边原来只有 1.0），Comfort Ayu Dark 的金色描边（10.5）也收敛了。
- VS Code 会把一些悬停和选中色块（活动栏与工具栏里当前图标的背景、失去焦点的列表选中项）填成纯灰，在底色带色调的主题里（Comfort Sunlit、Owl 和 Pale Dark）显得发灰、格格不入；现在这些色块改用底色的色相。
- 布局边框（例如拆分编辑器之间的分隔线）不再刺眼：与编辑区的对比度最高 1.6（Comfort Dracula Dark / Light 原来是 6.5 和 4.9，Comfort Pale Dark 是 2.8）。
- 每套主题现在都能通过 VS Code 颜色主题 schema 的校验：删掉 VS Code 会忽略或已弃用的颜色键（有替代键的改用新名称）；必须半透明的颜色恢复半透明，不再盖住文字；删掉 token 的背景色和其他会被忽略的 token 字段；另外给约 80 个以前漏掉、只能用默认值的界面色配了颜色。
- 语法规则现在来自同一个共享规则池，由全部原主题合并而成（约 1,300 个选择器，很多针对特定语言）；每条规则分配一个角色，再用各主题自己的角色色上色，所有主题因此有同样丰富的覆盖。去掉各主题专属的语义 token 颜色，改用 VS Code 内置的语义 token 到 TextMate 的映射。普通变量在每套主题里都有一种推导出的专属颜色，有色彩，又和参数、关键字、字符串、函数、类型明显分开。
- 原主题有意调暗的 scope（标点、docstring、嵌入代码的分隔符、注释里的 scope 等），以及原主题里为灰色的手工标注 scope，现在用角色色的暗化、非粗体变体，不再用完整的、有时还加粗的角色色。调色把两种本该不同的语法色挤到一起时（例如 Comfort GitHub Light 的字符串和常量，Comfort One Light 的数字和类型），会在明度上重新拉开，或在色相上稍微拉开。
- Markdown 在每套主题里都清爽好读：列表项不再染上常量色，列表符号用暗化的标题色，标题一律加粗，标题、行内代码、链接和引用不再共用一种颜色。
- 工作台更安静：按钮（例如「提交」）改为低饱和色，不再是饱和色块；深色和浅色主题的徽标都是低饱和的安静圆点（与编辑区对比度不超过 1.7，上面的字 4.5）；列表选中项（文件树、问题面板）接近中性色，文字用正文色；布局边框为中性色；被忽略的文件暗化到注释的对比度；侧栏和标题栏的标题保持可读。
- 深色主题的终端色不比正文亮（亮色和白色最多 1.2–1.25 倍），亮黄、亮青和白色不再刺眼；压暗后变灰的亮色恢复了色相。
- 源代码管理图里的分支标签在每套主题里都可读：标签文字重新使用面板背景色（Comfort One Dark 沿用了浅灰文字，在蓝色标签上几乎看不见），标签颜色与它的对比度至少 4.5。
- Less、CSS 和 SCSS 的属性名与属性值明显区分（Comfort Moka Dark 以前两者都是同一种青色）。
- CSS、Less、SCSS、Sass、JSON 和 TOML 里的属性名在每套主题里都有一种安静的专属颜色：取声明关键字的色相，暗化到最安静的语法层级，从不加粗或倾斜（以前与关键字同色，在 Comfort Sunlit 里还是粗体）。
- 所有主题的语法覆盖统一：同样 33 个常见 scope（类型、命名空间、变量、参数、对象键、Markdown 标题、粗体、斜体、引用、链接等）在每套主题里都有颜色；原主题没覆盖的，借用本主题里最接近的角色的颜色。

### 移除

- 原来的 **Comfort One Dark** 和 **Comfort One Light** 已并入之前的 Fit 主题，这两个名字现在归 Fit 主题使用。

## v0.0.2 2026-10-08

### 破坏性变更

- **One Dark Pro Lite** 改名为 **One Dark Fit**；用过它的话，更新后请在 Preferences: Color Theme（「首选项：颜色主题」）里重新选择。

### 新增

- **One Light Fit**：对 Atom One Light 2.3.0 的完整护眼改编，设计方式与 One Dark Fit 相同。底色从 `#FAFAFA` 调到 `#F3F3F3`，减少眩光；注释统一为 3.2，语法和终端颜色提到对比度下限，饱和度设了上限，所有写死的界面色都由主题接管。

### 变更

- **One Dark Fit**（原 One Dark Pro Lite）：从几乎照搬 One Dark Pro 改为完整的护眼改编。注释统一为 3.2，语法和终端颜色提到对比度下限，饱和度设了上限，界面文字的对比度有保证；现在能通过清晰度与护眼门槛。
- Comfort 主题文件和 Terminal.app 配置改名，加上 `comfort-` 前缀；导入的 Terminal.app 配置现在显示完整的主题名。重新导入 `.terminal` 文件即可用上新名称。
- **新图标**：一弯新月和一个太阳，下面一排主题色圆点，与 HeavenSky 的其他插件采用同样的扁平风格和强调色板。

## v0.0.1 2026-10-08

首次发布。七套主题都为舒适度做了调校和改编，色板参照官方主题设计。

### 新增

- **One Dark Pro Lite**：把 One Dark Pro 3.20.2 做成静态、无需设置的主题，开启斜体与粗体。
- **Comfort 主题**：One Dark、One Light、Ayu Dark、Ayu Light、Solarized Dark 和 Solarized Light，按 WCAG 对比度调校并限制饱和度，保留参考色相。
- 七套主题完整覆盖界面色，包括括号配对、集成终端，以及 VS Code 原本会留在写死默认值上的所有颜色。
- 为六套 Comfort 主题提供 macOS Terminal.app 配置。
