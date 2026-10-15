# Editor Comfort Theme

[![VS Marketplace](https://vsmarketplacebadges.dev/version-short/HeavenSky.editor-comfort-theme.svg?label=VS%20Marketplace)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![Installs](https://vsmarketplacebadges.dev/installs-short/HeavenSky.editor-comfort-theme.svg)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE.txt)

**English** · [简体中文](./README.zh-cn.md)

Sixteen VS Code color themes for long coding sessions. Each one keeps the colors of a popular theme — One Dark Pro, One Light, Ayu, Solarized, GitHub, Dracula, Night Owl, Monokai, One Monokai and Palenight — and only fixes what is hard to read, so it looks like the theme you know.

## Highlights

- **Original colors first** — backgrounds, body text and syntax colors stay exactly as in the original theme; a color changes only when it is hard to read, and only as much as needed.
- **Readable everywhere** — body text, syntax and terminal colors reach at least 4.5 contrast, comments 3.4, selections are visible, and text on badges, buttons and selected rows stays readable; a release gate checks every theme.
- **Complete coverage** — the ~200 UI colors VS Code otherwise hard-codes (terminal, diff, git decorations and more) and syntax rules the original leaves out are filled in from each theme's own palette, without changing any color the original sets.
- **Zero overhead** — static theme files only: no settings, no activation, no runtime code.
- **Matching terminal** — macOS Terminal.app profiles for every theme.

## Themes

| Theme | Original | Readability fixes |
| --- | --- | --- |
| **C One Dark** | One Dark Pro 3.20.2 | Line numbers and focus outline readable, terminal selection visible |
| **C One Light** | Atom One Light 2.3.0 | Comments 2.5 → 3.4, faint strings, types and constants raised to 4.5 |
| **C Ayu Dark** | ayu Mirage | Sidebar and activity bar text readable |
| **C Ayu Light** | ayu Light | Comments 2.2 → 3.4, faint strings, numbers and terminal colors raised to 4.5; badges and buttons readable |
| **C Sunlit Dark** | Solarized Dark | Comments 2.8 → 3.4, syntax colors from about 3.3 raised to 4.5, terminal selection visible |
| **C Sunlit Light** | Solarized Light | Body text 4.1 → 4.6, comments 2.5 → 3.4, syntax colors from about 3.0 raised to 4.5, editor and terminal selections visible |
| **C GitHub Dark** | GitHub Dark Dimmed 6.3.5 | Almost unchanged: badge text and find highlight |
| **C GitHub Light** | GitHub Light Default 6.3.5 | Almost unchanged: three faint terminal colors |
| **C Dracula Dark** | Dracula Soft 2.25.1 | Almost unchanged: badge text and input selection |
| **C Dracula Light** | Dracula's official Alucard light palette | New light design: Dracula Soft's structure recolored with Alucard on its cream background |
| **C Owl Dark** | Night Owl 2.1.1 | Diff inserted color and find highlight readable |
| **C Owl Light** | Night Owl Light 2.1.1 | Comments 2.6 → 3.4, faint regex, operators and properties raised to 4.5, terminal colors readable |
| **C Moka Dark** | One Monokai 0.5.2 | Comments 2.8 → 3.4 |
| **C Moka Light** | Classic Monokai palette | New light design: Monokai's text color `#F8F8F2` as the background, its background `#272822` as the text, accents deepened for a light background |
| **C Pale Dark** | Palenight 2.0.5 | Comments 2.8 → 3.4, sidebar and status bar text readable |
| **C Pale Light** | Palenight 2.0.5 hues | New light design: lavender background, deep violet-indigo text, Palenight's accents deepened so it stays clearly apart from C Owl Light |

Colors that are already readable are left as they are: no theme gets a new background, softer body text or toned-down accents. Themes are named `C <Name> Dark` and `C <Name> Light` (the theme ID in `settings.json` is the same, e.g. `"workbench.colorTheme": "C One Dark"`), so they never clash with the original themes.

Switch themes with **Preferences: Color Theme** (`⌘K ⌘T` / `Ctrl+K Ctrl+T`).

## Screenshots

Real VS Code windows: Source Control, TypeScript, Python and the terminal color matrix. Click the links under each shot for Explorer + Markdown + Less + Problems, and the Search view (focused search box) + Output panel.

| Dark | Light |
| --- | --- |
| **C One Dark**<br>![C One Dark](media/screenshots/one-dark-b.jpg)<br>[Explorer & Problems](media/screenshots/one-dark-a.jpg) · [Search & Output](media/screenshots/one-dark-c.jpg) | **C One Light**<br>![C One Light](media/screenshots/one-light-b.jpg)<br>[Explorer & Problems](media/screenshots/one-light-a.jpg) · [Search & Output](media/screenshots/one-light-c.jpg) |
| **C Ayu Dark**<br>![C Ayu Dark](media/screenshots/ayu-dark-b.jpg)<br>[Explorer & Problems](media/screenshots/ayu-dark-a.jpg) · [Search & Output](media/screenshots/ayu-dark-c.jpg) | **C Ayu Light**<br>![C Ayu Light](media/screenshots/ayu-light-b.jpg)<br>[Explorer & Problems](media/screenshots/ayu-light-a.jpg) · [Search & Output](media/screenshots/ayu-light-c.jpg) |
| **C Sunlit Dark**<br>![C Sunlit Dark](media/screenshots/sunlit-dark-b.jpg)<br>[Explorer & Problems](media/screenshots/sunlit-dark-a.jpg) · [Search & Output](media/screenshots/sunlit-dark-c.jpg) | **C Sunlit Light**<br>![C Sunlit Light](media/screenshots/sunlit-light-b.jpg)<br>[Explorer & Problems](media/screenshots/sunlit-light-a.jpg) · [Search & Output](media/screenshots/sunlit-light-c.jpg) |
| **C GitHub Dark**<br>![C GitHub Dark](media/screenshots/github-dark-b.jpg)<br>[Explorer & Problems](media/screenshots/github-dark-a.jpg) · [Search & Output](media/screenshots/github-dark-c.jpg) | **C GitHub Light**<br>![C GitHub Light](media/screenshots/github-light-b.jpg)<br>[Explorer & Problems](media/screenshots/github-light-a.jpg) · [Search & Output](media/screenshots/github-light-c.jpg) |
| **C Dracula Dark**<br>![C Dracula Dark](media/screenshots/dracula-dark-b.jpg)<br>[Explorer & Problems](media/screenshots/dracula-dark-a.jpg) · [Search & Output](media/screenshots/dracula-dark-c.jpg) | **C Dracula Light**<br>![C Dracula Light](media/screenshots/dracula-light-b.jpg)<br>[Explorer & Problems](media/screenshots/dracula-light-a.jpg) · [Search & Output](media/screenshots/dracula-light-c.jpg) |
| **C Owl Dark**<br>![C Owl Dark](media/screenshots/owl-dark-b.jpg)<br>[Explorer & Problems](media/screenshots/owl-dark-a.jpg) · [Search & Output](media/screenshots/owl-dark-c.jpg) | **C Owl Light**<br>![C Owl Light](media/screenshots/owl-light-b.jpg)<br>[Explorer & Problems](media/screenshots/owl-light-a.jpg) · [Search & Output](media/screenshots/owl-light-c.jpg) |
| **C Moka Dark**<br>![C Moka Dark](media/screenshots/moka-dark-b.jpg)<br>[Explorer & Problems](media/screenshots/moka-dark-a.jpg) · [Search & Output](media/screenshots/moka-dark-c.jpg) | **C Moka Light**<br>![C Moka Light](media/screenshots/moka-light-b.jpg)<br>[Explorer & Problems](media/screenshots/moka-light-a.jpg) · [Search & Output](media/screenshots/moka-light-c.jpg) |
| **C Pale Dark**<br>![C Pale Dark](media/screenshots/pale-dark-b.jpg)<br>[Explorer & Problems](media/screenshots/pale-dark-a.jpg) · [Search & Output](media/screenshots/pale-dark-c.jpg) | **C Pale Light**<br>![C Pale Light](media/screenshots/pale-light-b.jpg)<br>[Explorer & Problems](media/screenshots/pale-light-a.jpg) · [Search & Output](media/screenshots/pale-light-c.jpg) |

## Tuning principles

Every theme is built in three steps:

1. **Original** — the original theme as published (the three new light designs are generated from their dark originals first).
2. **Completion** — only what is missing is added. UI colors VS Code would otherwise hard-code take the hue of the theme's own terminal colors, with text at least as readable as VS Code's default (up to 4.5 contrast). Syntax rules come from a pool merged from all original themes and are added only for scopes the original leaves uncolored; a rule that would recolor a token the original already colors (for example an inner scope under a colored outer scope) is caught by tokenizing sample files and skipped.
3. **Readability fixes** — only the side that is hard to read changes, and only as far as needed, keeping hue and saturation: body text, syntax colors and terminal colors to 4.5 contrast, comments and dim terminal gray to 3.4, line numbers to 2.2, inactive UI text and focus outlines to 3.0; editor, input and terminal selections visible with readable text on them; text on badges, buttons and selected rows to 4.5 without flipping to the other side.

Adjustments for glare and comfort (capping brightness, removing neon, dimming backgrounds, compressing saturation and the like) still exist in the build tools but are off by default.

## Install

- **VS Code** — search `Editor Comfort Theme` in the Extensions view, or run `ext install HeavenSky.editor-comfort-theme` in the Command Palette.
- **Other VS Code–compatible editors** — download the `.vsix` from the [latest GitHub release](https://github.com/HeavenSky/editor-comfort-theme/releases) and run **Extensions: Install from VSIX…**.

Requires VS Code `1.101.0` or newer.

### Terminal.app profiles

Every theme has a matching macOS Terminal.app profile in the repository's [`terminal/`](./terminal/) folder. Double-click a `.terminal` file to import it. Importing does not replace an existing profile of the same name: Terminal adds a copy named `<name> 1`, so delete the old profile in Settings → Profiles first (or rename the copy afterwards).

## Turning off italic or bold

Themes are static, so there are no settings. Override font styles in your `settings.json` instead:

```jsonc
"editor.tokenColorCustomizations": {
	"textMateRules": [
		{ "scope": ["comment", "variable.parameter"], "settings": { "fontStyle": "" } }
	]
}
```

## License

[MIT](./LICENSE.txt). Built on One Dark Pro, One Light, ayu, VS Code's Solarized, GitHub, Dracula (including its Alucard palette), Night Owl, One Monokai and Palenight themes and the classic Monokai palette, all MIT — see [NOTICE.md](./NOTICE.md).
