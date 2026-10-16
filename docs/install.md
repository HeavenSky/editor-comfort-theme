# Install in VS Code or a compatible editor

**English** · [简体中文](../zh/docs/install.md)

This page covers every way to install the extension. You need VS Code 1.101.0 or newer, or an editor compatible with that version.

## Install in VS Code

Search `Editor Comfort Theme` in the Extensions view and click Install. You can also press `⌘P` / `Ctrl+P` and run:

```text
ext install HeavenSky.editor-comfort-theme
```

## Install in other editors

The extension is published only on the VS Code Marketplace. For editors that cannot install from it:

1. Download the `.vsix` file from the [latest GitHub release](https://github.com/HeavenSky/editor-comfort-theme/releases).
2. Run **Extensions: Install from VSIX…** from the Command Palette and choose the file.
3. Pick a theme as described in [Get started](../README.md#get-started).

## Fix an extension that will not install

- Symptom: installing fails with `Unable to install extension '<extension>' as it is not compatible with VS Code '<version>'.`
- Cause: the extension requires VS Code 1.101.0 or newer.
- Fix: update the editor, then install again.
