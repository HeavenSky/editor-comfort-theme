# TODO

- 主题调整只用门禁指标与脚本验证, 未在 VS Code 里逐套截图目视检查; 发版前建议逐套切换看一遍, 尤其是新增的 7 套与正文明显减淡的 GitHub Light, Dracula, Owl.
- 新增 Moka Light 后, README(中英), `package.nls*.json` 的主题数与列表, NOTICE, CHANGELOG 尚未同步, 等许可结论定了再改.
- 规则池新增 Monokai 带来的选择器中有 42 个属于需人工标注层(`uv run tools/pool.py`), 目前用推荐值; 可用 `--annotate` 页补标.
- 2026-10-12 整体调优(语法色彩度上限 0.10 → 0.085, 浅色正文 8.5 → 8.0, 浅色底亮度压到 0.85 以内, GitHub Light 最深语法色压到正文 0.9 倍)只经指标验证; 语法色整体变淡约 15%, 需在 VS Code 里目视确认辨识度可接受, 不满意可调 `tools/themes.py` 的 `SYNTAX_CAP`(0.08~0.09 柔和分差 1~3 分).
- 规则池复查(2026-10-12)已按规则自动处理: 弱化 / 灰白的选择器改为暗彩不加粗(`pool.MUTED_*`), 调色带来的撞色由 `gen_vscode.separate` 拉开; 审计脚本与报告在 `.ai-ctx/cache/sav_20261012_标注水分/`. 剩余: 7 对边缘撞色(Sunlit Light 属性名(标签)与声明类型都是近灰, Moka Dark 的 invalid 与正文, Moka Light 引用与 this, Pale 的暗彩函数与参数 ΔE 4.7); 各主题自身风格的加粗(One Dark 函数, Sunlit 关键字)保留未动.
- 标注页 / 复核页预览应按 fontStyle 渲染, 附对比度, 覆盖全部 14 套主题, 避免再次只凭色块决策.
- 2026-10-12 截图复查遗留(截图与审查记录在 `.ai-ctx/cache/sav_20261012_主题截图/`, 截图工具 `.ai-ctx/cache/vscode-render/shoot.mjs`): Graph 视图分支标签 `scmGraph.historyItemRefColor` 主题未定义, 用的是 VS Code 默认饱和蓝; 浅色主题终端 white 前景本就偏淡(惯例, 未改); 终端 dim 行由 VS Code 按 50% 透明度渲染, 主题无法单独调; Owl Dark 的 Markdown 标题与正文层级仍偏弱(已强制加粗); GitHub / Pale / Dracula 的 Markdown 标题与粗体比正文略亮(未改); Sunlit Dark 活动栏选中图标底偏蓝.
