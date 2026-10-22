# 主题文件的读取与颜色写法解析: 生成链(tools/gen)与检查脚本(tools/check)共用的唯一实现.
# 只依赖 colorlib, 不导入 tools/gen 下的模块: 那里的模块互相导入(gen_vscode -> separate -> pool 等), 放进任何一个都会成环.
import json, os, re

from colorlib import Rgb, h

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# 原主题(含 design.py 生成的浅色设计)
SOURCES = os.path.join(ROOT, 'assets', 'source')
_HEX = re.compile(r'#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})')


def load(path: str) -> dict:
    """读 VS Code 主题 JSON: 允许整行 // 注释与尾逗号(JSONC)."""
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', s))


def norm_hex(v) -> str | None:
    """颜色写法统一成大写 #RRGGBB / #RRGGBBAA(3 / 4 位展开); 不是 hex 时返回 None."""
    if not isinstance(v, str) or not _HEX.fullmatch(v):
        return None
    s = v[1:]
    return '#' + (''.join(c * 2 for c in s) if len(s) in (3, 4) else s).upper()


def parse(v) -> tuple[Rgb, str] | None:
    """(颜色, 透明度两位 hex 或 ''); 认 white / black 两个颜色名, 其余非 hex 返回 None."""
    if not isinstance(v, str):
        return None
    n = norm_hex({'white': '#FFFFFF', 'black': '#000000'}.get(v.lower(), v))
    return (h(n[1:7]), n[7:9]) if n else None
