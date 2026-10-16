# 在 Terminal.app 中使用主题

[English](../../docs/terminal-app.md) · **简体中文**

本页把同一套颜色装进 macOS Terminal.app。需要 macOS；配置文件放在 GitHub 仓库里，不随插件安装。

## 导入配置

1. 在下表打开对应主题的配置文件并下载（GitHub 页面上的 **Download raw file**）。
2. 双击下载的 `.terminal` 文件。Terminal.app 会用该主题的颜色打开新窗口，并添加一份以主题命名的配置（例如 `C One Dark`）。
3. 想让每个新窗口都用它：打开「终端」→「设置」→「描述文件」，选中该配置，点「默认」。

| 主题 | 配置文件 |
| --- | --- |
| C One Dark | [`one-dark.terminal`](../../assets/terminal/one-dark.terminal) |
| C One Light | [`one-light.terminal`](../../assets/terminal/one-light.terminal) |
| C Ayu Dark | [`ayu-dark.terminal`](../../assets/terminal/ayu-dark.terminal) |
| C Ayu Light | [`ayu-light.terminal`](../../assets/terminal/ayu-light.terminal) |
| C Sunlit Dark | [`sunlit-dark.terminal`](../../assets/terminal/sunlit-dark.terminal) |
| C Sunlit Light | [`sunlit-light.terminal`](../../assets/terminal/sunlit-light.terminal) |
| C GitHub Dark | [`github-dark.terminal`](../../assets/terminal/github-dark.terminal) |
| C GitHub Light | [`github-light.terminal`](../../assets/terminal/github-light.terminal) |
| C Dracula Dark | [`dracula-dark.terminal`](../../assets/terminal/dracula-dark.terminal) |
| C Dracula Light | [`dracula-light.terminal`](../../assets/terminal/dracula-light.terminal) |
| C Owl Dark | [`owl-dark.terminal`](../../assets/terminal/owl-dark.terminal) |
| C Owl Light | [`owl-light.terminal`](../../assets/terminal/owl-light.terminal) |
| C Moka Dark | [`moka-dark.terminal`](../../assets/terminal/moka-dark.terminal) |
| C Moka Light | [`moka-light.terminal`](../../assets/terminal/moka-light.terminal) |
| C Pale Dark | [`pale-dark.terminal`](../../assets/terminal/pale-dark.terminal) |
| C Pale Light | [`pale-light.terminal`](../../assets/terminal/pale-light.terminal) |

## 出现名为 `<name> 1` 的重复配置

- 症状：导入后，「设置」→「描述文件」里同时出现 `C One Dark` 和 `C One Dark 1`。
- 原因：导入不会覆盖已有的同名配置，Terminal.app 会另建一份副本。
- 解决：导入前先在「设置」→「描述文件」里删掉旧配置，或导入后删掉旧配置再给副本改名。
