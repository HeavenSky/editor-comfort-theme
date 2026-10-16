# Choose a theme

**English** · [简体中文](../zh/docs/themes.md)

This page helps you pick one of the sixteen themes and set it in `settings.json`. It assumes the extension is already installed ([Get started](../README.md#get-started)).

## Find your original theme

Each theme keeps the colors of one original and fixes only what is hard to read. The right column lists what changed; contrast values are WCAG contrast ratios against the editor background.

| Theme | Original | Readability fixes |
| --- | --- | --- |
| C One Dark | One Dark Pro 3.20.2 | Line numbers and focus outline readable, terminal selection visible |
| C One Light | Atom One Light 2.3.0 | Comments 2.5 → 3.4, faint strings, types and constants raised to 4.5 |
| C Ayu Dark | ayu Mirage | Sidebar and activity bar text readable |
| C Ayu Light | ayu Light | Comments 2.2 → 3.4, faint strings, numbers and terminal colors raised to 4.5; badges and buttons readable |
| C Sunlit Dark | Solarized Dark | Comments 2.8 → 3.4, syntax colors from about 3.3 raised to 4.5, terminal selection visible |
| C Sunlit Light | Solarized Light | Body text 4.1 → 4.6, comments 2.5 → 3.4, syntax colors from about 3.0 raised to 4.5, editor and terminal selections visible |
| C GitHub Dark | GitHub Dark Dimmed 6.3.5 | Almost unchanged: badge text and find highlight |
| C GitHub Light | GitHub Light Default 6.3.5 | Almost unchanged: three faint terminal colors |
| C Dracula Dark | Dracula Soft 2.25.1 | Near-white body text `#F6F6F4` toned down to `#D7D7D6`; badge text and input selection |
| C Dracula Light | Dracula's official Alucard light palette | New light design: Dracula Soft's structure recolored with Alucard on its cream background |
| C Owl Dark | Night Owl 2.1.1 | Diff inserted color and find highlight readable |
| C Owl Light | Night Owl Light 2.1.1 | Comments 2.6 → 3.4, faint regex, operators and properties raised to 4.5, terminal colors readable |
| C Moka Dark | One Monokai 0.5.2 | Comments 2.8 → 3.4 |
| C Moka Light | Classic Monokai palette | New light design: Monokai's text color `#F8F8F2` as the background, its background `#272822` as the text, accents deepened for a light background |
| C Pale Dark | Palenight 2.0.5 | Comments 2.8 → 3.4, sidebar and status bar text readable |
| C Pale Light | Palenight 2.0.5 hues | New light design: lavender background, deep violet-indigo text, Palenight's accents deepened so it stays clearly apart from C Owl Light |

Colors that already read well are left as they are. The one deliberate exception is near-white in dark themes, which is toned down slightly; see [How the colors are adjusted](how-themes-are-tuned.md#tone-down-near-white-in-dark-themes).

## Set a theme in settings.json

The theme ID in `settings.json` is the same as the name in the theme picker. The `C` prefix keeps the names apart from the original themes, so both can be installed side by side.

```jsonc
"workbench.colorTheme": "C One Dark"
```

To follow your operating system's light or dark mode, set one theme for each:

```jsonc
"window.autoDetectColorScheme": true,
"workbench.preferredDarkColorTheme": "C One Dark",
"workbench.preferredLightColorTheme": "C One Light"
```

## Compare the themes in screenshots

Every shot is a real VS Code window showing Source Control, TypeScript, Python and the terminal color matrix. The links under each shot open two more scenes: Explorer with Markdown, Less and the Problems panel, and the Search view with the Output panel.

| Dark | Light |
| --- | --- |
| C One Dark<br>![C One Dark](../media/screenshots/one-dark-b.jpg)<br>[Explorer & Problems](../media/screenshots/one-dark-a.jpg) · [Search & Output](../media/screenshots/one-dark-c.jpg) | C One Light<br>![C One Light](../media/screenshots/one-light-b.jpg)<br>[Explorer & Problems](../media/screenshots/one-light-a.jpg) · [Search & Output](../media/screenshots/one-light-c.jpg) |
| C Ayu Dark<br>![C Ayu Dark](../media/screenshots/ayu-dark-b.jpg)<br>[Explorer & Problems](../media/screenshots/ayu-dark-a.jpg) · [Search & Output](../media/screenshots/ayu-dark-c.jpg) | C Ayu Light<br>![C Ayu Light](../media/screenshots/ayu-light-b.jpg)<br>[Explorer & Problems](../media/screenshots/ayu-light-a.jpg) · [Search & Output](../media/screenshots/ayu-light-c.jpg) |
| C Sunlit Dark<br>![C Sunlit Dark](../media/screenshots/sunlit-dark-b.jpg)<br>[Explorer & Problems](../media/screenshots/sunlit-dark-a.jpg) · [Search & Output](../media/screenshots/sunlit-dark-c.jpg) | C Sunlit Light<br>![C Sunlit Light](../media/screenshots/sunlit-light-b.jpg)<br>[Explorer & Problems](../media/screenshots/sunlit-light-a.jpg) · [Search & Output](../media/screenshots/sunlit-light-c.jpg) |
| C GitHub Dark<br>![C GitHub Dark](../media/screenshots/github-dark-b.jpg)<br>[Explorer & Problems](../media/screenshots/github-dark-a.jpg) · [Search & Output](../media/screenshots/github-dark-c.jpg) | C GitHub Light<br>![C GitHub Light](../media/screenshots/github-light-b.jpg)<br>[Explorer & Problems](../media/screenshots/github-light-a.jpg) · [Search & Output](../media/screenshots/github-light-c.jpg) |
| C Dracula Dark<br>![C Dracula Dark](../media/screenshots/dracula-dark-b.jpg)<br>[Explorer & Problems](../media/screenshots/dracula-dark-a.jpg) · [Search & Output](../media/screenshots/dracula-dark-c.jpg) | C Dracula Light<br>![C Dracula Light](../media/screenshots/dracula-light-b.jpg)<br>[Explorer & Problems](../media/screenshots/dracula-light-a.jpg) · [Search & Output](../media/screenshots/dracula-light-c.jpg) |
| C Owl Dark<br>![C Owl Dark](../media/screenshots/owl-dark-b.jpg)<br>[Explorer & Problems](../media/screenshots/owl-dark-a.jpg) · [Search & Output](../media/screenshots/owl-dark-c.jpg) | C Owl Light<br>![C Owl Light](../media/screenshots/owl-light-b.jpg)<br>[Explorer & Problems](../media/screenshots/owl-light-a.jpg) · [Search & Output](../media/screenshots/owl-light-c.jpg) |
| C Moka Dark<br>![C Moka Dark](../media/screenshots/moka-dark-b.jpg)<br>[Explorer & Problems](../media/screenshots/moka-dark-a.jpg) · [Search & Output](../media/screenshots/moka-dark-c.jpg) | C Moka Light<br>![C Moka Light](../media/screenshots/moka-light-b.jpg)<br>[Explorer & Problems](../media/screenshots/moka-light-a.jpg) · [Search & Output](../media/screenshots/moka-light-c.jpg) |
| C Pale Dark<br>![C Pale Dark](../media/screenshots/pale-dark-b.jpg)<br>[Explorer & Problems](../media/screenshots/pale-dark-a.jpg) · [Search & Output](../media/screenshots/pale-dark-c.jpg) | C Pale Light<br>![C Pale Light](../media/screenshots/pale-light-b.jpg)<br>[Explorer & Problems](../media/screenshots/pale-light-a.jpg) · [Search & Output](../media/screenshots/pale-light-c.jpg) |

## Fix a theme that disappeared after an update

- Symptom: after updating, VS Code shows its default theme and the theme picker has no `Comfort <Name>` entries.
- Cause: your settings still name a theme from v0.0.3 or earlier, such as `Comfort One Dark`; the themes are now named `C <Name> Dark` and `C <Name> Light`.
- Fix: pick the theme again in **Preferences: Color Theme**, or replace the old names in `workbench.colorTheme`, `workbench.preferredDarkColorTheme` and `workbench.preferredLightColorTheme`.
