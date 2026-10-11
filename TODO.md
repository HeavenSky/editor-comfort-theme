# TODO

- 主题调整只用门禁指标与脚本验证, 未在 VS Code 里逐套截图目视检查; 发版前建议逐套切换看一遍, 尤其是新增的 7 套与正文明显减淡的 GitHub Light, Dracula, Night Owl.
- Monokai Pro 为商业许可(仅允许评估), 未收录; 如需 Monokai 系可考虑基于公开的经典 Monokai 色板自制.
- 规则池标注里有 12 组只差语言后缀的同类选择器角色不一致(如 `keyword.operator.expression.instanceof` 的 ts=标签 / tsx=关键字, `constant.length.units` 的 sass=变量), 待复核是否手误; 修改 `tools/sources/pool-overrides.json` 或重新打开标注页后重新生成.
