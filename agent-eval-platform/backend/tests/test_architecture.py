"""架构边界的自动检查。

为什么值得单独测：垂直切分的价值全靠边界撑着，而边界腐坏是无声的 —— 随手写一个
跨域 import，代码照常跑、测试照常绿，几个月后目录结构就名存实亡。写在文档里靠自觉
管不住，尤其 AI 辅助编码时最容易顺手 import 到隔壁域。

这里不禁止一切跨域调用（那不现实），而是要求**跨域依赖必须显式申报**：
新增一条未登记的跨域 import 就会红，逼你要么改设计、要么把它加进白名单并说明理由。
"""
import ast
import os

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")

# 允许的跨域依赖：(来源域, 目标域) -> 为什么
ALLOWED_CROSS_DOMAIN = {
    ("*", "identity"): "鉴权是横切关注点，各域都要用 identity.deps 取当前用户与空间",
    ("quality", "evaluation"): "回归门禁要复用评估器执行逻辑",
    ("identity", "governance"): "空间管理的高风险操作要走审计标记",
}

# 分层：越靠前越底层，底层不得依赖上层
LAYER_ORDER = ["shared", "core", "domains", "pipeline"]


def _iter_modules(pkg):
    """产出 (相对路径, ast 树)。"""
    root = os.path.join(APP, pkg)
    if not os.path.isdir(root):
        return
    for dirpath, _, filenames in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, APP).replace("\\", "/")
            with open(p, encoding="utf-8") as f:
                yield rel, ast.parse(f.read(), filename=rel)


def _imports_of(tree, rel):
    """解析出这个模块引用到的 app 内顶层包（以及域名）。

    相对 import 要按 level 还原成绝对路径，否则 `from ..evaluation.service import x`
    这类跨域引用会被漏掉。
    """
    parts = rel.split("/")[:-1]          # 所在包路径
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level == 0:
                continue                  # 绝对 import（第三方库），不管
            base = parts[: len(parts) - (node.level - 1)] if node.level > 1 else parts
            target = base + ((node.module or "").split(".") if node.module else [])
            if target:
                out.append(target)
    return out


def test_shared_depends_on_nothing_inside_app():
    """shared/ 是最底层，依赖任何 app 内的包都会形成向上依赖。"""
    bad = []
    for rel, tree in _iter_modules("shared"):
        for t in _imports_of(tree, rel):
            if t and t[0] in LAYER_ORDER:
                bad.append(f"{rel} → {'/'.join(t)}")
    assert not bad, "shared/ 不得依赖 app 内其他包：\n" + "\n".join(bad)


def test_core_does_not_depend_on_domains_or_pipeline():
    """core/ 是基础设施，依赖业务域就形成了倒置。"""
    bad = []
    for rel, tree in _iter_modules("core"):
        for t in _imports_of(tree, rel):
            if t and t[0] in ("domains", "pipeline"):
                bad.append(f"{rel} → {'/'.join(t)}")
    assert not bad, "core/ 不得依赖 domains/ 或 pipeline/：\n" + "\n".join(bad)


def test_cross_domain_imports_are_declared():
    """域之间的依赖必须在 ALLOWED_CROSS_DOMAIN 里登记过。"""
    undeclared = []
    for rel, tree in _iter_modules("domains"):
        src_domain = rel.split("/")[1]
        for t in _imports_of(tree, rel):
            if not t or t[0] != "domains":
                continue
            if len(t) < 2:
                continue
            dst_domain = t[1]
            if dst_domain == src_domain:
                continue
            if ("*", dst_domain) in ALLOWED_CROSS_DOMAIN:
                continue
            if (src_domain, dst_domain) in ALLOWED_CROSS_DOMAIN:
                continue
            undeclared.append(f"{rel} → domains/{dst_domain}")
    assert not undeclared, (
        "发现未申报的跨域 import。要么改设计，要么把它加进 ALLOWED_CROSS_DOMAIN 并写明理由：\n"
        + "\n".join(undeclared))


def test_every_domain_has_init():
    """每个域都要是合法的包，否则 import 会以难懂的方式失败。"""
    root = os.path.join(APP, "domains")
    missing = [d for d in os.listdir(root)
               if os.path.isdir(os.path.join(root, d)) and d != "__pycache__"
               and not os.path.exists(os.path.join(root, d, "__init__.py"))]
    assert not missing, f"这些域缺 __init__.py：{missing}"


def test_all_tables_are_collected_by_metadata():
    """聚合入口必须把所有域的模型都 import 到。

    挡的是这个真实故障：拆分 models.py 后漏 import 某个域，Base.metadata 少收几张表，
    建表时静默跳过 —— 不报错，只在运行时报「表不存在」。
    """
    from app import models  # noqa: F401
    from app.core.db import Base

    collected = set(Base.metadata.tables)
    declared = set()
    for rel, tree in _iter_modules("domains"):
        if not rel.endswith("/models.py"):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == "__tablename__":
                        if isinstance(node.value, ast.Constant):
                            declared.add(node.value.value)
    missing = declared - collected
    assert not missing, f"这些表在域里声明了却没被 metadata 收集到：{sorted(missing)}"
