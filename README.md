# Editor Comfort Theme

[![VS Marketplace](https://vsmarketplacebadges.dev/version-short/HeavenSky.editor-comfort-theme.svg?label=VS%20Marketplace)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![Installs](https://vsmarketplacebadges.dev/installs-short/HeavenSky.editor-comfort-theme.svg)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE.txt)

**English** · [简体中文](./README.zh-cn.md)

Thirteen VS Code color themes for long coding sessions, every one tuned and adapted for comfort. The palettes take their design cues from popular themes — One Dark Pro, One Light, Ayu, Solarized, GitHub, Dracula, Night Owl, One Monokai and Palenight — so they feel familiar from the first line.

## Highlights

- **Comfort-tuned throughout** — all thirteen themes are adapted for long sessions and pass the same gate: WCAG contrast, OKLCH chroma, plus softness and eye-fatigue scores.
- **Familiar by design** — palettes reference the official themes; hues are kept while lightness and chroma are tuned.
- **Complete coverage** — the ~200 UI colors VS Code otherwise hard-codes (bracket pairs, terminal, diff and more) are set from each theme's own palette.
- **Zero overhead** — static theme files only: no settings, no activation, no runtime code.
- **Matching terminal** — macOS Terminal.app profiles for every theme.

## Themes

| Theme | Palette reference | Comfort adjustments |
| --- | --- | --- |
| **One Dark Fit** | One Dark Pro 3.20.2 | Keeps One Dark Pro's background, body text, italic, bold and orange terminal yellow; softer accents, comments easier to read |
| **One Light Fit** | Atom One Light 2.3.0 | Background dimmed (`#FAFAFA` → `#F0F0F2`), body text softened, softer accents |
| **Comfort Ayu Dark** | ayu Mirage | Body text softened, calmer strings, readable punctuation |
| **Comfort Ayu Light** | ayu Light | Background dimmed, darker text |
| **Comfort Solarized Dark** | Solarized Dark | Brighter text, softer accents |
| **Comfort Solarized Light** | Solarized Light | Background dimmed, darker text |
| **Comfort GitHub Dark Dimmed** | GitHub Dark Dimmed 6.3.5 | Slightly softer text and accents; keeps the gray-blue background |
| **Comfort GitHub Light** | GitHub Light Default 6.3.5 | Pure white background dimmed, body text softened from 15.8 to 8.5 contrast |
| **Comfort Dracula** | Dracula Soft 2.25.1 | Body text softened from 13.2 to 7.0 contrast, softer accents |
| **Comfort Night Owl** | Night Owl 2.1.1 | Near-black background lifted (keeping its deep blue), body text softened from 13.5 to 7.0 contrast |
| **Comfort Night Owl Light** | Night Owl Light 2.1.1 | Near-white background dimmed, comments much easier to read |
| **Comfort One Monokai** | One Monokai 0.5.2 | Softer Monokai accents on the One Dark background |
| **Comfort Palenight** | Palenight 2.0.5 | Body text and accents softened |

Every theme passes the same gate: body text, comments and line numbers in a comfortable contrast band, accents no louder than body text, near-neutral panels and no glaring highlights. **Fit** themes stay closest to their reference theme.

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

Every theme has a matching macOS Terminal.app profile in the repository's [`terminal/`](./terminal/) folder. Double-click a `.terminal` file to import it; a profile with the same name is replaced. Run `bash terminal/terminal-preview.sh --full` to show the 16-color matrix.

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
- `tools/sources/vscode-color-registry.json`: the VS Code color registry — core colors, the terminal palette and colors contributed by built-in extensions, each with its defaults and whether it must be translucent or is deprecated. Keys whose default is hard-coded and that the template leaves undefined are filled from the theme's own palette; after a VS Code upgrade, re-extract it with `npm run extract:registry`.
- Every generated theme is checked against `vscode://schemas/color-theme` (`tools/schema.py`): unregistered or deprecated color keys are dropped (deprecated keys with an official successor are renamed), colors that must be translucent are converted to an equivalent translucent value, and token rule fields VS Code ignores (token backgrounds, `fontStyle: normal`) are removed or rewritten. Run `uv run tools/schema.py <file>...` to check any theme.
- Syntax coverage is unified (`tools/coverage.py`): every theme colors the same 33 common scopes (types, namespaces, variables, parameters, properties, object keys, Markdown headings, bold, italic, quotes, links and more). Scopes a template leaves undefined borrow the theme's own color for the nearest role. Punctuation is deliberately left out: quotes and comment markers sit inside strings and comments and should keep those colors.

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
uv run tools/metrics.py --strict --check <file>...  # also require the softness and fatigue ratings to pass
uv run tools/metrics.py --detail <file>...  # list every softness / fatigue sub-metric and its score
```

- Contrast is always WCAG contrast; chroma is OKLCH C; background luminance is WCAG relative luminance (0 is pure black, 1 is pure white).
- Clarity is rated high / mid-high / mid and eye comfort good / mid. A theme passes when clarity is at least mid-high, eye comfort is good, and a VS Code theme covers every non-deprecated registry key with a hard-coded default ("uncovered" is 0) has no schema problems ("schema" is 0) and colors every common scope ("scopes" is 0). Scores only count colors VS Code actually applies.
- VS Code themes have two more upper limits; exceeding either rates clarity as mid: comment contrast at most 4.2, and in dark themes the brightest syntax color at most 1.1× the body text contrast. Line numbers need a contrast of at least 2.0; a dark theme rates high clarity only with body text contrast between 7.0 and 8.5.
- **Softness** and **fatigue** are scored 0–100 (rules in `tools/comfort.py`): a sub-metric inside its ideal range scores 100, drops to 60 at its limit, and fails beyond it.
  - Softness: average and maximum syntax chroma, lightness spread of the colored syntax colors, brightest syntax color versus body text, panel background chroma.
  - Fatigue: body text contrast, comment contrast, the gap between body text and comments, line number contrast, background luminance, bright panels (large backgrounds above 1.6 contrast against the editor) and highlight backgrounds that glare or make text hard to read.
  - They are enforced with `--strict`; `npm run metrics` and `npm run check` pass it by default, so every theme must pass them.
- Thresholds are the constants at the top of `tools/metrics.py`. `tune` in `tools/colorlib.py` is the tuning tool: cap chroma, then push lightness to the contrast minimum, without changing hue.
- "Default text on a colored background" (such as `\e[41m` alone) is unreadable under any palette and is not scored; Terminal.app dims faint text by a fixed, non-configurable ratio.

### Theme similarity

`tools/similar.py` compares VS Code color themes item by item (CIEDE2000 color difference), finds pairs that are close overall with only a few clearly different spots, and groups those spots by color pair; after picking groups it can write a merge preview and run the gate on it:

```bash
npm run similar                                              # compare all themes pairwise
uv run tools/similar.py a.json b.json --merge out.json --take 1,3   # base on a, take groups 1 and 3 from b
```

### Before release

```bash
npm run check       # icon, manifest, template drift, generated theme drift, color gate
npm run typecheck
npm test
npm run package     # build artifacts/editor-comfort-theme-<version>.vsix and assert its contents
```

With npm 12, `npm ci` only accepts a lockfile resolved from `registry.npmjs.org`, and dependency install scripts (`esbuild`, `@vscode/vsce-sign`, `fsevents`) are skipped by default. None of them is needed to check, test or package; approve one with `npm install-scripts approve <package>` only if signing or publishing locally fails. CI uses the npm bundled with the Node version in `.nvmrc` and is not affected.

This repository derives from the vsc-ext project template; `npm run check` reports any drift of the shared template files.

## License

[MIT](./LICENSE.txt). Built on One Dark Pro, One Light, ayu and VS Code's Solarized themes, all MIT — see [NOTICE.md](./NOTICE.md).
