"""模块文档字符串: 应为暗彩."""
import os


class Loader(object):
    """类文档字符串."""

    def load(self, path: str, retries: int = 3) -> dict:
        # 注释
        value = os.environ.get("HOME", None)
        data = {"path": path, "count": 42, "ok": True}
        return {**data, "value": f"{value}\n"}
