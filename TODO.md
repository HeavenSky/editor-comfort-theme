# TODO

改主题阶段(门禁规则已定, 见 `tools/comfort.py` 与 `tools/metrics.py`):

- 生成器 `fill_hardcoded` 用 `accent()` 补 VS Code 硬编码默认色时只按色相取终端色、不看明度, 背景类键(`inputValidation.*Background`, `debugExceptionWidget.background`, `mergeEditor.changeBase*`, `list.dropBackground` 等)被填成亮色块; 背景类键应保持接近编辑区底的明度.
- 生成器 `UI_PAIRS` 行号下限 3.0 改为目标 2.2(门禁下限 2.0, 防疲劳理想 2.0~2.6).
- 生成器注释由固定 `COMMENT_CR = 3.2` 改为随正文联动: 正文 / 1.85, 限制在 3.4~4.2.
- 8 套主题整体降彩度, 使语法色平均彩度落到 0.07 附近(柔和限值 0.10); 浅色主题正文对比度(约 10)降到 9 以内.
- 合并: Comfort One Light 并入 One Light Fit(`npm run similar` 判为可合并); One Dark 两套可考虑合并, 终端黄保留 One Dark Fit 的 `#D18F52`. 合并会减少已发布主题, 需处理已在用被删主题的用户.
- README 里 "Comfort 比 Fit 更柔和" 的说法与实测相反, 改主题后同步.
- 主题调完、全部通过 `--strict` 后, 把 `--strict` 并入 `npm run metrics` 与 `scripts/check-extra.mjs` 的默认门禁.
