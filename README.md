# Editor Comfort Theme

**English** · [简体中文](./zh/README.md)

Sixteen familiar VS Code themes in dark and light that keep their original colors and fix only what is hard to read: One, Ayu, Sunlit (Solarized), GitHub, Dracula, Owl (Night Owl), Moka (One Monokai / Monokai) and Pale (Palenight).

[![VS Marketplace](https://vsmarketplacebadges.dev/version-short/HeavenSky.editor-comfort-theme.svg?label=VS%20Marketplace)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![Installs](https://vsmarketplacebadges.dev/installs-short/HeavenSky.editor-comfort-theme.svg)](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE.txt)

If you like a popular theme but squint at its comments, faint strings or an invisible terminal selection, these versions fix exactly those colors and leave the rest alone. Patching colors yourself in `settings.json` fixes one spot at a time; here every theme is checked against the same contrast floor, and UI colors the original leaves to VS Code's generic defaults are filled in from the theme's own palette.

![C One Dark: Source Control, TypeScript, Python and the terminal color matrix](media/screenshots/one-dark-b.jpg)

## Get started

1. Install from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=HeavenSky.editor-comfort-theme), or press `⌘P` / `Ctrl+P` and run `ext install HeavenSky.editor-comfort-theme`.
2. Run **Preferences: Color Theme** from the Command Palette (`⇧⌘P` / `Ctrl+Shift+P`), or press `⌘K ⌘T` / `Ctrl+K Ctrl+T`, and pick a theme named `C <Name> Dark` or `C <Name> Light`, for example `C One Dark`. The editor, the workbench and the integrated terminal switch to the new colors at once.

## Keep the theme you know

**Backgrounds, body text and syntax colors stay as in the original theme.** A color changes only when it is hard to read, and only as far as needed, keeping its hue and saturation. C GitHub Dark is almost identical to GitHub Dark Dimmed, while C Sunlit Light raises the contrast of Solarized Light's comments from 2.5 to 3.4. See [what changed in each theme](docs/themes.md#find-your-original-theme).

## Read every line without squinting

Body text, syntax colors and the terminal's normal and bright colors have a contrast ratio of at least 4.5, and comments at least 3.4. Editor, input and terminal selections stay visible, and the text on them stays readable. Sidebar, badge and button text is raised until it reads well next to the theme's body text. The rules are listed in [How the colors are adjusted](docs/how-themes-are-tuned.md).

## Get a fully themed workbench

Diff, git decoration, terminal and other UI colors match the theme instead of VS Code's generic defaults: where the original leaves them unset, they take the theme's own hues. Syntax rules the original leaves out are added only for scopes it leaves uncolored, so no color the original sets is overwritten.

## Use the same colors in Terminal.app

Every theme has a matching macOS Terminal.app profile. [Import a profile](docs/terminal-app.md) by double-clicking its `.terminal` file.

## Nothing to configure

The extension is static theme files only: no settings, no activation and no runtime code. To turn off italics or override a color, use VS Code's own settings as shown in [Customize a theme](docs/customize.md).

## When not to use it

If you want a softer, dimmer or redesigned look, these themes are the wrong fit: they deliberately keep the original's brightness and saturation. If the original theme already reads well for you, keep using it.

## Learn more

- [Documentation](docs/README.md): installing in other editors, every theme with screenshots, Terminal.app profiles and customization.
- [Changelog](./CHANGELOG.md): what changed in each release.

## License

[MIT](./LICENSE.txt). Built on MIT-licensed themes; the sources and palette credits are listed in [NOTICE.md](./NOTICE.md).
