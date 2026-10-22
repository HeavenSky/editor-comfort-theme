# /// script
# requires-python = ">=3.11"
# ///
# 从本机 VS Code 安装包一次提取两份数据(只读取, 不执行安装包内任何代码), 写入 assets/vscode/:
#   color-docs.json      全部颜色键的说明与四种主题类型的默认值表达式(extract_key_docs.build)
#   color-registry.json  颜色注册表: 硬编码默认色, 须半透明, 已废弃, 语义 token 选择器(extract_registry.build)
# VS Code 升级后重跑, 再运行 npm run gen:themes.
# 用法: uv run tools/gen/extract_vscode.py [VS Code.app 路径] [输出目录]
#   颜色说明有解析失败项时仍写入, 退出码 1; 注册表认不出安装包形态时不写注册表, 退出码 1
import json, os, sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_key_docs, extract_registry

APP = '/Applications/Visual Studio Code.app'
OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'vscode'))


def main() -> int:
    app = sys.argv[1] if len(sys.argv) > 1 else APP
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    res = os.path.join(app, 'Contents', 'Resources', 'app')
    src = open(os.path.join(res, 'out', 'vs', 'workbench', 'workbench.desktop.main.js'), encoding='utf-8', errors='replace').read()
    version = json.load(open(os.path.join(res, 'package.json')))['version']
    os.makedirs(out, exist_ok=True)
    rc = 0

    docs, failed = extract_key_docs.build(res, src, version)
    path = os.path.join(out, 'color-docs.json')
    json.dump(docs, open(path, 'w', encoding='utf-8'), indent='\t', ensure_ascii=False)
    print(f"VS Code {version}: {docs['count']} 键, 说明与默认值完整 {docs['ok']}, 失败 {len(failed)} -> {os.path.relpath(path)}")
    for k, v in list(failed.items())[:40]:
        print('  失败', k, v)
    rc |= bool(failed)

    reg = extract_registry.build(res, src, version)
    if isinstance(reg, str):
        print(f'{reg}, 未写入 color-registry.json', file=sys.stderr)
        return 1
    path = os.path.join(out, 'color-registry.json')
    json.dump(reg, open(path, 'w', encoding='utf-8'), indent='\t')
    colors = reg['colors'].values()
    print(f"VS Code {version}: {len(colors)} 个颜色键, dark 下硬编码默认值 {sum(1 for v in colors if v['dark'])} 个, "
          f"须半透明 {sum(1 for v in colors if v['transparent'])} 个, 已废弃 {sum(1 for v in colors if v['deprecated'])} 个 -> {os.path.relpath(path)}")
    return rc


if __name__ == '__main__':
    sys.exit(main())
