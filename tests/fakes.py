"""测试用的假 OpenAI 客户端（不联网）。"""
from __future__ import annotations

from types import SimpleNamespace

try:  # 新版 openai SDK 使用 httpx2，旧版使用 httpx
    import httpx2 as httpx
except ImportError:  # pragma: no cover
    import httpx

REQ = httpx.Request("POST", "https://api.openai.com/v1/responses")


class FakeResp:
    def __init__(self, text, status="completed", reason=None):
        self.status, self.output_text = status, text
        self.incomplete_details = SimpleNamespace(reason=reason) if reason else None
        self.usage = SimpleNamespace(model_dump=lambda mode=None: {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})

    def model_dump(self, mode=None):
        return {"status": self.status, "output_text": self.output_text}


class FakeClient:
    """按顺序依次返回/抛出预设的结果；记录每次调用的参数。"""
    def __init__(self, *script):
        self.script, self.calls = list(script), []
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
