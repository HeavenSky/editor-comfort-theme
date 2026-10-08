# Editor Comfort Theme

[![Marketplace](https://img.shields.io/visual-studio-marketplace/v/HeavenSky.editor-comfort-theme?label=marketplace)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/HeavenSky.editor-comfort-theme)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/LICENSE.txt)

**English** · [简体中文](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/README.zh-cn.md)

Seven VS Code color themes for long coding sessions, every one tuned and adapted for comfort. The palettes take their design cues from the official One Dark Pro, One Light, Ayu and Solarized themes, so they feel familiar from the first line.

## Highlights

- **Comfort-tuned throughout** — all seven themes are adapted for long sessions and pass the same WCAG contrast and OKLCH chroma gate.
- **Familiar by design** — palettes reference the official themes; hues are kept while lightness and chroma are tuned.
- **Complete coverage** — the ~200 UI colors VS Code otherwise hard-codes (bracket pairs, terminal, diff and more) are set from each theme's own palette.
- **Zero overhead** — static theme files only: no settings, no activation, no runtime code.
- **Matching terminal** — macOS Terminal.app profiles for all six Comfort themes.

## Themes

| Theme | Palette reference | Comfort adjustments |
| --- | --- | --- |
| **One Dark Pro Lite** | One Dark Pro 3.20.2 | Closest to the original: body text kept, more of the original chroma retained within the gate; italic and bold enabled |
| **Comfort One Dark** | One Dark Pro | Softer accents, slightly brighter text |
| **Comfort One Light** | Atom One Light | Dimmer background, softer accents |
| **Comfort Ayu Dark** | ayu Mirage | Softer accents, calmer strings, readable punctuation |
| **Comfort Ayu Light** | ayu Light | Dimmer background, darker text |
| **Comfort Solarized Dark** | Solarized Dark | Brighter text, softer accents |
| **Comfort Solarized Light** | Solarized Light | Dimmer background, darker text |

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

The six Comfort themes have matching macOS Terminal.app profiles in the repository's [`terminal/`](https://github.com/HeavenSky/editor-comfort-theme/tree/HEAD/terminal) folder. Double-click a `.terminal` file to import it.

## Turning off italic or bold

Themes are static, so there are no settings. Override font styles in your `settings.json` instead:

```jsonc
"editor.tokenColorCustomizations": {
	"textMateRules": [
		{ "scope": ["comment", "variable.parameter"], "settings": { "fontStyle": "" } }
	]
}
```

## For contributors

Themes are generated, not hand-edited. Palettes and tuning parameters live in `tools/themes.py`; `tools/metrics.py` prints clarity and eye-comfort scores for any theme file and fails with `--check` when a theme falls short. See [README.zh-cn.md](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/README.zh-cn.md) for the full workflow.

## License

[MIT](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/LICENSE.txt). Built on One Dark Pro, One Light, ayu and VS Code's Solarized themes, all MIT — see [NOTICE.md](https://github.com/HeavenSky/editor-comfort-theme/blob/HEAD/NOTICE.md).
