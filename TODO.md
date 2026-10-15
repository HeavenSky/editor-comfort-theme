# TODO

## 方案待定

- v0.0.4 已在本地提交(`chore: 发布 v0.0.4`), 门禁与打包已过, 未推送也未打标签; 待确认后执行 `git push origin main` 与 `git tag v0.0.4 && git push origin v0.0.4`, 标签推送会触发 Release 工作流发布到两个市场

## 方案确定

## 确定不修

- Owl Dark 字符串 #ECC48D 与类型 #FFCB8B 近色(主要角色色差 3.79), 终端黄 #C5E478 色相 122° 在黄槽(55~115°)外; 不修: 用户定保留 Night Owl 原配色, 两处都是原主题原值
- Sunlit Dark / Light 原语法色对比度 3.25~4.75 / 2.93~4.29 几乎全低于 4.5, syntax_floor 统一抬到 4.5 左右, 明暗层次被压平; 不修: 用户定维持; Solarized 各彩色按相近明度设计, 原对比度跨度只有约 1.46 倍, 压平损失的层次有限
- Dracula Dark 粉色活动栏徽标 #F286C4 上白字 2.16, 只调底色要变 ΔE 20.2(超过 NUDGE_MAX_DE 15)才到 4.92, 已换成深色字 #282A36(6.09); 不修: 用户定维持
- full-rule.json 颜色映射里有 123 个固定色(One Light 33, Owl Light 27, One Dark 19, Owl Dark 14, 其余 30): 原主题的角色色在它自己的颜色键里找不到同色键(如 One Dark 字符串 #98C379 与它的终端绿不同色); 不修: 用户定维持; 固定色就是原主题该角色的原值, 补全按它上色即还原原色. 颜色映射由 pool.color_map 读原主题(不读 full)计算, 在补全段补终端色不会减少固定色
- 发布前检查只核对 one-dark-full.json(其余 full 由 complete.py --check 现写, 随后 gen_vscode --check 用它们核对 themes/, 补全段的漂移仍会在主题生成物一致性上暴露); 不修: 用户定维持
- metrics.py fidelity 只给相对原主题的偏离, 未给相对 full 的(方案写了); 不修: 用户定不做, 全关时等于 full 已由恒等校验保证, 默认档相对 full 的偏离就是调色步骤的改动量
- 补全段给原主题未定义的括号色 1~3 补主题色(按 constant.numeric / keyword.control / constant.character.escape 解析), 替代 VS Code 默认色(深色 金 #FFD700 / 紫 #DA70D6 / 蓝 #179FFF, 浅色 蓝 #0431FA / 绿 #319331 / 棕 #7B3814), 是截图差异最普遍的来源; 不修: 维持补全全盘接受, 括号色随主题色板; 4~6 保持透明(VS Code 只循环前 3 色)
