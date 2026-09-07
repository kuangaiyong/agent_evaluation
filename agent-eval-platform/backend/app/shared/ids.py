"""主键生成。被所有域使用，故放 shared/。"""
import uuid


def uid(prefix=""):
    return prefix + uuid.uuid4().hex[:8]
