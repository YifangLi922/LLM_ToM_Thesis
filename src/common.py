"""公共工具：路径、JSONL 读写、哈希、答案标准化。不依赖任何 API。"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
# guideline v1.1：完整规范（Part A + Part B，给研究者/代码看，用于校验与存档，**不发给造题模型**）
GUIDELINE_PATH = REPO_ROOT / "generator_guideline_v1_1.md"
# 发给造题模型的 prompt（仅 Part A）
MODEL_PROMPT_PATH = REPO_ROOT / "generator_model_prompt_v1_1.md"
GUIDELINE_VERSION = "1.1"
# pilot 阶段的 12 条锁定事实
KNOWLEDGE_PATH = REPO_ROOT / "knowledge_pool_pilot_12_v1.jsonl"
CONFIG_PATH = REPO_ROOT / "config" / "pilot.yaml"


# --------------------------------------------------------------------------- 哈希 / JSON
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    """文件内容的 SHA-256（用作 guideline 的版本标识）。统一换行，避免 Windows/Linux 换行差异。"""
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


# --------------------------------------------------------------------------- JSONL
class JsonlError(ValueError):
    """JSONL 解析失败，消息里带行号。"""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise JsonlError(f"{path}:{lineno}: JSON 解析失败: {e}") from e
            if not isinstance(obj, dict):
                raise JsonlError(f"{path}:{lineno}: 每行必须是 JSON 对象")
            rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


# --------------------------------------------------------------------------- 答案标准化
_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
         "eighty": 80, "ninety": 90}
_COMPOUND = re.compile(r"\b(" + "|".join(_TENS) + r")[\s-]+(" + "|".join(k for k in _UNITS if 0 < _UNITS[k] < 10) + r")\b")
_SINGLE = re.compile(r"\b(" + "|".join(list(_UNITS) + list(_TENS)) + r")\b")


def normalize_answer(text: str) -> str:
    """小写、去首尾空白与末尾标点、合并空格，并把英文数字词（0-99）换成阿拉伯数字。

    只用于"两个答案是否实质相同"的保守比较，不是评分器（评分器在后续里程碑实现）。
    """
    s = re.sub(r"\s+", " ", str(text).strip().lower())
    s = s.strip(" .,:;!?\"'")
    s = _COMPOUND.sub(lambda m: str(_TENS[m.group(1)] + _UNITS[m.group(2)]), s)
    s = _SINGLE.sub(lambda m: str(_UNITS.get(m.group(1), _TENS.get(m.group(1)))), s)
    return s


def answers_equivalent(a: str, b: str) -> bool:
    """保守判断：标准化后完全相同才算相同（"3 October" 与 "3 November" 不会被误判为相同）。"""
    return normalize_answer(a) == normalize_answer(b)


def contains_word(text: str, token: str) -> bool:
    """token 是否作为独立词/数字出现在 text 中（大小写不敏感）。"""
    t = token.strip()
    if not t:
        return False
    return re.search(r"(?<![\w])" + re.escape(t) + r"(?![\w])", text, flags=re.IGNORECASE) is not None
