"""检查 OPENROUTER_API_KEY 是否配置正确、是否有效，以及剩余额度。**不会打印 key。**

用法：
    python src/check_openrouter_access.py

只做一次免费的"查询当前 key 信息"请求（GET /api/v1/key），不调用任何模型，不花钱。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

URL = "https://openrouter.ai/api/v1/key"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("未找到 OPENROUTER_API_KEY。请在仓库根目录的 .env 里加一行：OPENROUTER_API_KEY=你的key")
        return 1
    problems = []
    if key != key.strip("\"' "):
        problems.append("key 两端似乎带了引号或空格，请去掉")
    if not key.startswith("sk-or-"):
        problems.append("key 不是以 sk-or- 开头，可能复制错了（OpenRouter 的 key 通常以 sk-or-v1- 开头）")
    for p in problems:
        print("提示：", p)

    req = urllib.request.Request(URL, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8")).get("data", {})
    except urllib.error.HTTPError as e:
        print(f"请求失败：HTTP {e.code}。" + ("key 无效、已被删除或复制不完整。" if e.code in (401, 403) else ""))
        return 2
    except urllib.error.URLError as e:
        print("网络错误：", e.reason)
        return 2

    print("OpenRouter key 有效。")
    for k in ("label", "limit", "limit_remaining", "usage", "is_free_tier"):
        if k in data:
            print(f"  {k}: {data[k]}")
    print("（label 只显示 key 的名字/末几位，不是完整 key）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
