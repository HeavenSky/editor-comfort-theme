# TODO

- 主题调整只用门禁指标与脚本验证, 未在 VS Code 里逐套截图目视检查; 发版前建议逐套切换看一遍, 尤其是新增的 7 套与正文明显减淡的 GitHub Light, Dracula, Night Owl.
- Monokai Pro 为商业许可(仅允许评估), 未收录; 如需 Monokai 系可考虑基于公开的经典 Monokai 色板自制.
- 规则池还有 317 个选择器待人工标注(未标注时用推荐值): 运行 `uv run tools/pool.py --annotate .ai-ctx/cache/sav_20261011_规则池标注/annotate.html` 打开页面标注, 导出存为 `tools/sources/pool-overrides.json` 后重新生成.
