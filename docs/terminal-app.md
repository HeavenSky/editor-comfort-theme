# Use the themes in Terminal.app

**English** · [简体中文](../zh/docs/terminal-app.md)

This page gets the matching colors into macOS Terminal.app. You need macOS; the profiles live in the GitHub repository and are not part of the installed extension.

## Import a profile

1. Open the profile for your theme from the table below and download it (**Download raw file** on GitHub).
2. Double-click the downloaded `.terminal` file. Terminal.app opens a new window in the theme's colors and adds the profile, named after the theme (for example `C One Dark`).
3. To use it for every new window, open Terminal → Settings → Profiles, select the profile and click Default.

| Theme           | Profile                                                               |
| --------------- | --------------------------------------------------------------------- |
| C One Dark      | [`one-dark.terminal`](../assets/terminal/one-dark.terminal)           |
| C One Light     | [`one-light.terminal`](../assets/terminal/one-light.terminal)         |
| C Ayu Dark      | [`ayu-dark.terminal`](../assets/terminal/ayu-dark.terminal)           |
| C Ayu Light     | [`ayu-light.terminal`](../assets/terminal/ayu-light.terminal)         |
| C Sunlit Dark   | [`sunlit-dark.terminal`](../assets/terminal/sunlit-dark.terminal)     |
| C Sunlit Light  | [`sunlit-light.terminal`](../assets/terminal/sunlit-light.terminal)   |
| C GitHub Dark   | [`github-dark.terminal`](../assets/terminal/github-dark.terminal)     |
| C GitHub Light  | [`github-light.terminal`](../assets/terminal/github-light.terminal)   |
| C Dracula Dark  | [`dracula-dark.terminal`](../assets/terminal/dracula-dark.terminal)   |
| C Dracula Light | [`dracula-light.terminal`](../assets/terminal/dracula-light.terminal) |
| C Owl Dark      | [`owl-dark.terminal`](../assets/terminal/owl-dark.terminal)           |
| C Owl Light     | [`owl-light.terminal`](../assets/terminal/owl-light.terminal)         |
| C Moka Dark     | [`moka-dark.terminal`](../assets/terminal/moka-dark.terminal)         |
| C Moka Light    | [`moka-light.terminal`](../assets/terminal/moka-light.terminal)       |
| C Pale Dark     | [`pale-dark.terminal`](../assets/terminal/pale-dark.terminal)         |
| C Pale Light    | [`pale-light.terminal`](../assets/terminal/pale-light.terminal)       |

## What a profile changes

A profile changes only how the window looks; keyboard and shell behavior stay at Terminal.app's defaults.

- Colors: background, text, bold text, cursor, selection and the 16 ANSI colors come from the theme. Bold text keeps its color instead of switching to the bright variant.
- Window: 120 × 30 with a blinking vertical-bar cursor, and the title bar shows neither the profile name nor the window size. Closing a window never asks for confirmation.
- Font: the profiles are built with Maple Mono NF CN at 12 pt. To use another font, change it under Settings → Profiles → Text.
- Option does not act as Meta. To turn that on, select **Use Option as Meta key** under Settings → Profiles → Keyboard.

## Fix a duplicate profile named `<name> 1`

- Symptom: after importing, Settings → Profiles shows both `C One Dark` and `C One Dark 1`.
- Cause: importing never replaces an existing profile with the same name; Terminal.app adds a copy instead.
- Fix: delete the old profile in Settings → Profiles before importing, or delete it afterwards and rename the copy.
