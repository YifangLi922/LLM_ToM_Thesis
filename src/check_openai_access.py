"""检查当前 OPENAI_API_KEY 能访问哪些模型（用于确定"造题模型"）。

用法（在仓库根目录、已激活虚拟环境）：
    python src/check_openai_access.py                       # 列出模型
    python src/check_openai_access.py --all                 # 连 embedding/语音等也列出
    python src/check_openai_access.py --test MODEL_ID       # 对指定模型各发一次极小的调用
    python src/check_openai_access.py --test MODEL_ID --structured   # 同时测试 Structured Outputs

密钥从环境变量或仓库根目录的 .env 读取；本脚本绝不打印密钥。
"""
from __future__ import annotations

import argparse
import os
import re
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv 不是必须的，也可直接设置环境变量
    pass

from openai import APIError, OpenAI
from pydantic import BaseModel

# 与"文本造题"无关的模型类型，默认隐藏
NOT_TEXT_GEN = re.compile(
    r"embedding|whisper|tts|dall-e|image|moderation|audio|realtime|transcribe|sora|davinci|babbage",
    re.I,
)


class Pong(BaseModel):
    word: str


def describe_error(e: Exception) -> str:
    status = getattr(e, "status_code", None)
    msg = getattr(e, "message", str(e))
    return f"{type(e).__name__} (HTTP {status}): {str(msg)[:200]}"


def list_models(client: OpenAI, show_all: bool) -> None:
    try:
        ids = sorted(m.id for m in client.models.list())
    except APIError as e:
        print("列出模型失败：", describe_error(e))
        print("可能是受限 key 没有读取模型列表的权限；这不代表不能调用模型，请改用 --test 直接试。")
        return
    shown = ids if show_all else [i for i in ids if not NOT_TEXT_GEN.search(i)]
    print(f"共 {len(ids)} 个模型，显示 {len(shown)} 个：")
    for i in shown:
        print("  ", i)
    print("\n注意：出现在列表里不保证一定能调用（项目可能限制了模型/额度），请用 --test 实测。")


def test_model(client: OpenAI, model: str, structured: bool) -> None:
    print(f"\n=== 测试 {model} ===")
    try:
        # 推理型模型会先消耗 token 思考，所以 max_output_tokens 不宜太小
        r = client.responses.create(
            model=model,
            input="Reply with the single word: OK",
            max_output_tokens=300,
        )
        print("基本调用: 成功 | status =", r.status, "| 输出 =", repr(r.output_text[:50]))
        u = r.usage
        if u:
            print("  token 用量: input =", u.input_tokens, "output =", u.output_tokens)
    except APIError as e:
        print("基本调用: 失败 ->", describe_error(e))
        return
    if structured:
        try:
            r = client.responses.parse(
                model=model,
                input="Return the word OK.",
                text_format=Pong,
                max_output_tokens=300,
            )
            print("Structured Outputs: 成功 ->", r.output_parsed)
        except Exception as e:  # noqa: BLE001 - 诊断脚本，需要看到所有失败原因
            print("Structured Outputs: 失败 ->", describe_error(e))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="显示所有模型，包括非文本生成类")
    ap.add_argument("--test", nargs="+", metavar="MODEL_ID", help="对这些模型各做一次极小的测试调用")
    ap.add_argument("--structured", action="store_true", help="--test 时同时测试 Structured Outputs")
    args = ap.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("未找到 OPENAI_API_KEY：请在仓库根目录的 .env 里写入 OPENAI_API_KEY=... 或设置环境变量。")

    client = OpenAI()
    if args.test:
        for m in args.test:
            test_model(client, m, args.structured)
    else:
        list_models(client, args.all)


if __name__ == "__main__":
    main()
