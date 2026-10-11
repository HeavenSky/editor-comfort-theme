# Change Log

## Unreleased

### Added

- Seven new themes, adapted automatically from their originals and tuned to the same gate: **Comfort GitHub Dark** (from GitHub Dark Dimmed), **Comfort GitHub Light**, **Comfort Dracula Dark** (from Dracula Soft), **Comfort Night Owl Dark**, **Comfort Night Owl Light**, **Comfort One Monokai Dark** and **Comfort Pale Night Dark** (from Palenight).
- Terminal.app profiles for Comfort One Dark and Comfort One Light, so every theme now has one.

### Changed

- All themes retuned for a softer, less tiring look: accents less saturated, comments brighter and tied to body text contrast, dimmer line numbers, body text no harsher than 7.5 (dark) or 8.5 (light) contrast, panels near neutral and highlights no longer glaring. Bright validation, merge and drop backgrounds that used to flash in some panels are fixed.
- **Comfort One Light** now uses the dimmer `#F0F0F2` background.
- Every theme now validates against VS Code's color theme schema: dropped color keys VS Code ignores or has deprecated (renaming those with a successor), made colors that must be translucent translucent again so they no longer cover text, removed token background colors and other ignored token fields, and themed about 80 more UI colors whose defaults were previously missed.
- Syntax rules now come from one shared pool built from all original themes (about 1,300 selectors, many language-specific), each assigned a role and colored with every theme's own role colors, so all themes share the same rich coverage. Theme-specific semantic token colors are dropped in favor of VS Code's built-in semantic-to-TextMate mapping. Ordinary variables get a derived color of their own in every theme, colorful yet clearly apart from parameters, keywords, strings, functions and types.
- Syntax coverage unified across all themes: the same 33 common scopes (types, namespaces, variables, parameters, object keys, Markdown headings, bold, italic, quotes, links and more) are colored everywhere, borrowing each theme's own color for the nearest role where its original left them out.
- Theme names simplified to `Comfort <Name> Dark` / `Comfort <Name> Light`: One Dark Fit → **Comfort One Dark**, One Light Fit → **Comfort One Light**. Theme files and Terminal.app profiles follow the same `comfort-<name>-dark|light` names, with compound names split into short words (`comfort-pale-night-dark`); Comfort Solarized Dark / Light are renamed **Comfort Sunlit Dark / Light**; reselect your theme and re-import the `.terminal` files.

### Removed

- The previous **Comfort One Dark** and **Comfort One Light** were merged into the former Fit themes, which now carry those names.

## v0.0.2 2026-10-08

### Added

- **One Light Fit**: a full eye-comfort adaptation of Atom One Light 2.3.0, designed the same way as One Dark Fit. Background eased from `#FAFAFA` to `#F3F3F3` to reduce glare, comments unified at 3.2, syntax and terminal colors brought to the contrast floor, chroma capped and every hard-coded UI color themed.

### Changed

- **One Dark Fit** (formerly One Dark Pro Lite): reworked from a near-copy of One Dark Pro into a full eye-comfort adaptation. Comments unified at 3.2, syntax and terminal colors brought to the contrast floor, chroma capped and UI text contrast secured; now passes the clarity and eye-comfort gate.
- Comfort theme files and Terminal.app profiles renamed with a `comfort-` prefix; imported Terminal.app profiles now show the full theme name. Re-import the `.terminal` files to pick up the new names.
- **New icon**: a crescent moon and a sun above a row of theme color dots, drawn in the same flat style and accent palette as the other HeavenSky extensions.

## v0.0.1 2026-10-08

Initial release. All seven themes are tuned and adapted for comfort, with palettes designed after the official themes.

### Added

- **One Dark Pro Lite**: One Dark Pro 3.20.2 as a static, settings-free theme with italic and bold enabled.
- **Comfort themes**: One Dark, One Light, Ayu Dark, Ayu Light, Solarized Dark and Solarized Light, tuned for WCAG contrast and capped chroma with reference hues preserved.
- Full UI color coverage in all seven themes, including bracket pairs, the integrated terminal and every color VS Code would otherwise leave at a hard-coded default.
- macOS Terminal.app profiles for the six Comfort themes.
