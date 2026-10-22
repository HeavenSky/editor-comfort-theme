# How the colors are adjusted

**English** · [简体中文](../zh/docs/how-themes-are-tuned.md)

This page explains which colors differ from the original theme and why, so you can predict what a theme will look like. Contrast values are WCAG contrast ratios against the background the color sits on.

## Start from the original theme

Every theme starts as the original theme exactly as published. The three new light designs, C Dracula Light, C Moka Light and C Pale Light, are first generated from their dark originals and then go through the same steps. The theme-by-theme list of originals is in [Choose a theme](themes.md#find-your-original-theme).

## Fill in only what is missing

**Completion adds colors the original leaves unset and never recolors one it sets.**

- UI colors that VS Code would otherwise hard-code, such as terminal, diff and git decoration colors, take the hue of the theme's own terminal colors. Text on them is at least as readable as with VS Code's defaults; where the defaults exceed 4.5, the requirement is capped at 4.5.
- Syntax rules come from a pool merged from all original themes and are added only for scopes the original leaves uncolored.
- Some pool rules would recolor, through an outer scope, a token the original already colors. The build finds them by tokenizing sample files and skips them.
- Bracket pair colors 1–3 use the theme's own colors; 4–6 stay unset, as in VS Code.

## Fix only what is hard to read

**Of a color and its background, only the one causing the problem changes, and only as far as needed, keeping hue and saturation.**

| What                                                       | Minimum |
| ---------------------------------------------------------- | ------- |
| Body text                                                  | 4.5     |
| Syntax colors                                              | 4.5     |
| Terminal normal and bright colors                          | 4.5     |
| Comments                                                   | 3.4     |
| Terminal dim gray (ANSI `90m`)                             | 3.4     |
| Body text on selections, find matches and other highlights | 3.5     |

- Editor and input selections are made visible, starting from the original selection color and changing only what is needed.
- The terminal selection is recomputed from the theme's terminal blue when the original one is barely visible or the text on it is hard to read.
- The current find match stands out more than the other matches.
- UI text and lines are raised until they read well next to the theme's body text. Each UI color falls into one of four tiers: content (sidebar text, text on badges and buttons), dimmed (line numbers, input placeholders), line (borders, focus outlines) and background (selected rows). Each tier's minimum is set relative to the contrast of the theme's own body text and calibrated on eight UI reference themes.
- Translucent colors first gain opacity; after that, only their lightness changes.
- Text that must flip from light to dark, or the reverse, to read on its background takes the theme's editor background or body text color when that reads better. For example, the text on C Dracula Dark's pink badge becomes `#282A36`.
- Colors the theme leaves unset, which VS Code works out from other colors, are left as VS Code computes them.
- Borders and background layers that the original makes indistinguishable from the surface they sit on (OKLab ΔE below 0.02) are left alone, because the original does not mean to draw them; focus outlines, selections and the current match are still made visible.

## Tell different kinds of code apart

**When two kinds of code that should look different share one color, one of them takes another color from the same theme, until the theme is as clear as the five clearest syntax themes.**

- Kinds are syntax roles such as keywords, functions, strings, types, numbers, constants, tags and comments. Which pairs must differ is decided by surveying 25 popular theme families: a pair that at least 75% of them clearly separate must be separated. Any other pair is separated only if at least three of the five clearest syntax themes (SynthWave '84, Ayu, Atom One Dark, Noctis and Tomorrow Night Blue) separate it.
- Pairs are checked on 20 short code samples, such as a YAML config, a shell script and Markdown with code blocks, wherever both kinds appear in the same sample, not only on the same line.
- The new color always comes from the theme itself: a color its syntax already uses, or one of its six terminal colors (red, green, yellow, blue, magenta and cyan) raised to the 4.5 syntax minimum, clearly different from the old one (CIEDE2000 ΔE of at least 10).
- Minor roles such as constants, built-ins and parameters change first. Keywords, functions, strings, types and tags, which usually carry a theme's identity, change only when nothing else is enough. Where the theme's dark or light counterpart is clearer, the new color follows it: C Owl Light's strings turn gold because Night Owl gives strings a warm peach.
- A theme stops changing once it has no more clashes than the median of the five clearest syntax themes.
- One exception: two identity roles that at least 90% of the families separate, such as strings and types, are separated even after that point, as long as recoloring the role with fewer tokens is enough. That is why C Owl Dark's types turn yellow while its peach strings stay.

## Tone down near-white in dark themes

Near-white colors in dark themes, such as `#FFFFFF`, are lowered to OKLCH lightness 0.88 with their hue kept. This applies to body text, UI text, icons and lines, syntax colors and the terminal's white. For example, C Dracula Dark's body text goes from `#F6F6F4` to `#D7D7D6`, and the terminal's bright white in C Ayu Dark, C Owl Dark and C Pale Dark goes from `#FFFFFF` to `#D7D7D7`.

## What is left alone

No theme gets a new editor background, dimmer body text other than near-white, or less saturated accent colors.
