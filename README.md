# Editor Comfort Theme

[![Marketplace](https://img.shields.io/visual-studio-marketplace/v/HeavenSky.editor-comfort-theme?label=marketplace)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/HeavenSky.editor-comfort-theme)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/LICENSE.txt)

**English** · [简体中文](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/README.zh-cn.md)

Eight VS Code color themes for long coding sessions, every one tuned and adapted for comfort. The palettes take their design cues from the official One Dark Pro, One Light, Ayu and Solarized themes, so they feel familiar from the first line.

## Highlights

- **Comfort-tuned throughout** — all eight themes are adapted for long sessions and pass the same WCAG contrast and OKLCH chroma gate.
- **Familiar by design** — palettes reference the official themes; hues are kept while lightness and chroma are tuned.
- **Complete coverage** — the ~200 UI colors VS Code otherwise hard-codes (bracket pairs, terminal, diff and more) are set from each theme's own palette.
- **Zero overhead** — static theme files only: no settings, no activation, no runtime code.
- **Matching terminal** — macOS Terminal.app profiles for all six Comfort themes.

## Themes

| Theme | Palette reference | Comfort adjustments |
| --- | --- | --- |
| **One Dark Fit** | One Dark Pro 3.20.2 | Full eye-comfort adaptation: comments unified, syntax and terminal colors lifted to the contrast floor, chroma capped, every hard-coded UI color themed; keeps One Dark Pro's body text, italic and bold |
| **One Light Fit** | Atom One Light 2.3.0 | Full eye-comfort adaptation: glare reduced (`#FAFAFA` → `#F3F3F3`), comments unified, syntax and terminal colors lifted to the contrast floor, chroma capped, every hard-coded UI color themed; keeps One Light's body text |
| **Comfort One Dark** | One Dark Pro | Softer accents, slightly brighter text |
| **Comfort One Light** | Atom One Light | Dimmer background, softer accents |
| **Comfort Ayu Dark** | ayu Mirage | Softer accents, calmer strings, readable punctuation |
| **Comfort Ayu Light** | ayu Light | Dimmer background, darker text |
| **Comfort Solarized Dark** | Solarized Dark | Brighter text, softer accents |
| **Comfort Solarized Light** | Solarized Light | Dimmer background, darker text |

**Fit** themes add a full eye-comfort adaptation while keeping the character of their reference theme; **Comfort** themes go further toward a softer, quieter look.

Switch themes with **Preferences: Color Theme** (`⌘K ⌘T` / `Ctrl+K Ctrl+T`).

## Tuning principles

Every theme is tuned color by color against three goals:

- **Clarity** — body text, syntax colors, line numbers and terminal colors meet a minimum WCAG contrast against their background.
- **Calm** — comments share one quiet contrast level (3.2) across all themes; in dark themes no syntax color exceeds 1.1× the contrast of body text.
- **Eye comfort** — accent chroma is capped; dark backgrounds avoid pure black and light backgrounds avoid pure white.

## Install

- **VS Code** — search `Editor Comfort Theme` in the Extensions view, or run `ext install HeavenSky.editor-comfort-theme` in the Command Palette.
- **Other VS Code–compatible editors** — download the `.vsix` from the [latest GitHub release](https://github.com/HeavenSky/editor-comfort-theme/releases) and run **Extensions: Install from VSIX…**.

Requires VS Code `1.101.0` or newer.

### Terminal.app profiles

The six Comfort themes have matching macOS Terminal.app profiles in the repository's [`terminal/`](https://github.com/HeavenSky/editor-comfort-theme/tree/HEAD/terminal) folder. Double-click a `.terminal` file to import it; a profile with the same name is replaced. Run `bash terminal/terminal-preview.sh --full` to show the 16-color matrix.

## Turning off italic or bold

Themes are static, so there are no settings. Override font styles in your `settings.json` instead:

```jsonc
"editor.tokenColorCustomizations": {
	"textMateRules": [
		{ "scope": ["comment", "variable.parameter"], "settings": { "fontStyle": "" } }
	]
}
```

## Development

### Changing colors

`themes/*.json` and `terminal/*.terminal` are generated. Do not edit them by hand: the next generation overwrites them, and `npm run check` reports the drift. The generator inputs are:

- `tools/themes.py`: each theme's target background, foreground, 16 terminal colors and tuning parameters (chroma cap, contrast minimums for syntax and comment colors).
- `tools/sources/*.json`: the reference theme templates. Every theme keeps all UI keys and syntax rules of its template and only transforms colors one by one.
- `tools/sources/vscode-color-registry.json`: the VS Code color registry. Keys whose default is hard-coded and that the template leaves undefined are filled from the theme's own palette; after a VS Code upgrade, re-extract it with `npm run extract:registry`.

```bash
npm run extract:registry              # extract the color registry from /Applications/Visual Studio Code.app
uv run tools/gen_vscode.py            # generate themes/*.json
uv run tools/gen_terminal.py          # generate terminal/*.terminal (macOS only); accepts --font <PostScript name> --size <points>
npm run metrics                       # metrics table and gate verdict; exits 1 when a theme falls short
```

### Metrics and gate

`tools/metrics.py` works on its own and accepts any `.terminal` profile or VS Code color theme `.json`, including other people's themes:

```bash
uv run tools/metrics.py <file>...           # print the metrics table only
uv run tools/metrics.py --check <file>...   # also apply the gate
```

- Contrast is always WCAG contrast; chroma is OKLCH C; background luminance is WCAG relative luminance (0 is pure black, 1 is pure white).
- Clarity is rated high / mid-high / mid and eye comfort good / mid. A theme passes when clarity is at least mid-high, eye comfort is good, and a VS Code theme covers every registry key with a hard-coded default ("uncovered" is 0).
- VS Code themes have two more upper limits; exceeding either rates clarity as mid: comment contrast at most 3.5, and in dark themes the brightest syntax color at most 1.1× the body text contrast.
- Thresholds are the constants at the top of `tools/metrics.py`. `tune` in `tools/colorlib.py` is the tuning tool: cap chroma, then push lightness to the contrast minimum, without changing hue.
- "Default text on a colored background" (such as `\e[41m` alone) is unreadable under any palette and is not scored; Terminal.app dims faint text by a fixed, non-configurable ratio.

### Before release

```bash
npm run check       # icon, manifest, template drift, generated theme drift, color gate
npm run typecheck
npm test
npm run package     # build artifacts/editor-comfort-theme-<version>.vsix and assert its contents
```

This repository derives from the vsc-ext project template. Because it has no runtime code, a few template files deviate in a controlled way; the reasons are recorded on the `!` lines of `.template-shared`.

## License

[MIT](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/LICENSE.txt). Built on One Dark Pro, One Light, ayu and VS Code's Solarized themes, all MIT — see [NOTICE.md](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/NOTICE.md).
