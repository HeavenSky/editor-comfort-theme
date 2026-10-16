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

**Only the side that is hard to read changes, and only as far as needed, keeping hue and saturation.**

| What | Minimum |
| --- | --- |
| Body text | 4.5 |
| Syntax colors | 4.5 |
| Terminal normal and bright colors | 4.5 |
| Comments | 3.4 |
| Terminal dim gray (`90m`) | 3.4 |
| Body text on selections, find matches and other highlights | 3.5 |

- Editor and input selections are made visible, starting from the original selection color and changing only what is needed.
- The terminal selection is recomputed from the theme's terminal blue when the original one is barely visible or the text on it is hard to read.
- The current find match stands out more than the other matches.
- UI colors such as sidebar text, line numbers, borders, badges, buttons and selected rows are sorted into four tiers: content, dimmed, line and background. Each tier's minimum is set relative to the theme's own body text and calibrated on eight reference themes. Translucent colors first gain opacity; after that, only their lightness changes.
- Borders and background layers that the original makes indistinguishable from the surface they sit on (OKLab ΔE below 0.02) are left alone, because the original does not mean to draw them; focus outlines, selections and the current match are still made visible.

## Tone down near-white in dark themes

Near-white colors in dark themes, such as `#FFFFFF`, are lowered to OKLCH lightness 0.88 with their hue kept. This applies to body text, UI text, icons and lines, syntax colors and the terminal's white. For example, C Dracula Dark's body text goes from `#F6F6F4` to `#D7D7D6`, and the terminal's bright white in C Ayu Dark, C Owl Dark and C Pale Dark goes from `#FFFFFF` to `#D7D7D7`.

## What is left alone

No theme gets a new background, dimmer body text other than near-white, or toned-down accents.
