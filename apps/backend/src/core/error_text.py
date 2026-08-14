from __future__ import annotations


def describe_exception(exc: BaseException) -> str:
    """返回可诊断的异常文本，避免无参数异常生成空白问题记录。"""

    message = str(exc).strip()
    return message or repr(exc)


__all__ = ["describe_exception"]
