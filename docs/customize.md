# Customize a theme

**English** · [简体中文](../zh/docs/customize.md)

This page shows how to turn off italic or bold and how to change single colors. The themes have no settings of their own, so everything goes into your user `settings.json` through VS Code's built-in overrides.

## Turn off italic or bold

Set `fontStyle` to an empty string for the scopes you want upright and in regular weight. This example covers comments and parameters:

```jsonc
"editor.tokenColorCustomizations": {
	"textMateRules": [
		{ "scope": ["comment", "variable.parameter"], "settings": { "fontStyle": "" } }
	]
}
```

C Ayu Dark and C Ayu Light also italicize default-library interfaces through semantic highlighting, which `textMateRules` does not reach. Turn that off separately:

```jsonc
"editor.semanticTokenColorCustomizations": {
	"rules": { "interface.defaultLibrary": { "italic": false } }
}
```

## Change a color in one theme only

Put the override under the theme name in square brackets, so other themes are unaffected. This example changes the current line highlight in C One Dark:

```jsonc
"workbench.colorCustomizations": {
	"[C One Dark]": { "editor.lineHighlightBackground": "#2C313A" }
}
```

The same bracket form works inside `editor.tokenColorCustomizations` for syntax colors.
