# 在 VS Code 或兼容编辑器中安装

[English](../../docs/install.md) · **简体中文**

本页列出全部安装方式。需要 VS Code 1.101.0 及以上，或与该版本兼容的编辑器。

## 在 VS Code 中安装

在扩展视图搜索 `Editor Comfort Theme`，点安装。也可以按 `⌘P` / `Ctrl+P` 后执行：

```text
ext install HeavenSky.editor-comfort-theme
```

## 在其他编辑器中安装

插件只发布在 VS Code 插件市场。编辑器无法从那里安装时：

1. 从 [GitHub Release](https://github.com/HeavenSky/editor-comfort-theme/releases) 下载最新的 `.vsix` 文件。
2. 在命令面板执行 **Extensions: Install from VSIX…**（中文界面为「扩展：从 VSIX 安装…」），选中该文件。
3. 按[快速上手](../README.md#快速上手)里的做法选一套主题。

## 插件装不上

- 症状：安装失败，提示 `无法安装扩展“<extension>”，因为它与 VS Code“<version>”不兼容。`
- 原因：插件要求 VS Code 1.101.0 及以上。
- 解决：升级编辑器后重新安装。
