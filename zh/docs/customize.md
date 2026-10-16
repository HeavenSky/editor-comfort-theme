# 自定义主题

[English](../../docs/customize.md) · **简体中文**

本页说明怎样关掉斜体或粗体、怎样只改个别颜色。主题本身没有设置项，改动都写进用户 `settings.json`，用的是 VS Code 自带的覆盖设置。

## 关掉斜体或粗体

想让某些 scope 改回正体和常规粗细，就把它们的 `fontStyle` 设为空字符串。下例针对注释和参数：

```jsonc
"editor.tokenColorCustomizations": {
	"textMateRules": [
		{ "scope": ["comment", "variable.parameter"], "settings": { "fontStyle": "" } }
	]
}
```

C Ayu Dark 和 C Ayu Light 还通过语义高亮把默认库里的接口设成斜体，`textMateRules` 管不到这一处，要另外关掉：

```jsonc
"editor.semanticTokenColorCustomizations": {
	"rules": { "interface.defaultLibrary": { "italic": false } }
}
```

## 只改某一套主题的颜色

把覆盖写在方括号括起的主题名下，其他主题不受影响。下例修改 C One Dark 的当前行高亮：

```jsonc
"workbench.colorCustomizations": {
	"[C One Dark]": { "editor.lineHighlightBackground": "#2C313A" }
}
```

语法色同样可以在 `editor.tokenColorCustomizations` 里用这种方括号写法。
