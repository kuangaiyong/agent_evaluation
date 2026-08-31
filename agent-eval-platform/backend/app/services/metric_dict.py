"""指标字典的解析与同步。

权威源是文档 `智能体评测体系/01-指标体系与指标字典.md`，本模块只负责把它读成结构化行。
解析是纯函数（不碰 DB），便于用真实文档直接测；写库走 `sync_metrics`，按 code 幂等 upsert。

文档里每个指标长这样，格式在 92 条上完全一致：

    **A-01 · 任务成功率（Success Rate, SR）** ｜ L2 · 环境与交互

    - **定义**：……
    - **公式**：`SR = …`
    - **采集**：……
    - **陷阱**：……
    - **阈值**：……

注意分隔符是全角竖线 U+FF5C（｜），不是半角 |。
"""
import re

from sqlalchemy.orm import Session

from .. import models

# `### A 组 · 效果与完成度`
GROUP_RE = re.compile(r"^###\s+([A-Z])\s*组\s*·\s*(.+?)\s*$", re.M)
# `**A-01 · 任务成功率（Success Rate, SR）** ｜ L2 · 环境与交互`
HEADER_RE = re.compile(r"^\*\*([A-Z])-(\d{2})\s*·\s*(.+?)\*\*\s*｜\s*(.+?)\s*$", re.M)
# `- **定义**：……` —— 标签不写死，任何加粗标签的条目都收下，避免静默丢正文。
# 文档里除了固定五项，还有 `陷阱一`/`陷阱二`、`实测量级`、`注入哪几类故障` 这类变体，
# 它们恰恰带着 arXiv 出处的实测数字，丢了等于把引用依据丢了。
FIELD_RE = re.compile(r"^-\s+\*\*(.+?)\*\*\s*[：:]\s*(.+?)\s*$", re.M)

FIELD_TO_COLUMN = {"定义": "definition", "公式": "formula", "采集": "collection",
                   "陷阱": "pitfall", "阈值": "threshold"}
TEXT_COLUMNS = ("definition", "formula", "collection", "pitfall", "threshold", "notes")


def _column_for(label: str) -> str:
    """标签 → 列名。`陷阱一`/`陷阱二` 归到 pitfall，其余未登记标签一律进 notes。"""
    if label in FIELD_TO_COLUMN:
        return FIELD_TO_COLUMN[label]
    for known, column in FIELD_TO_COLUMN.items():
        if label.startswith(known):
            return column
    return "notes"


def parse_dictionary(text: str) -> list[dict]:
    """把 01 分册原文解析成指标行。顺序与文档一致。"""
    text = text.replace("\r\n", "\n")
    groups = {m.group(1): m.group(2) for m in GROUP_RE.finditer(text)}

    headers = list(HEADER_RE.finditer(text))
    rows = []
    for i, m in enumerate(headers):
        group_code, seq, name, layer_pillar = m.groups()
        # 正文 = 本条头部之后到下一条头部（或文末）之间
        body = text[m.end(): headers[i + 1].start() if i + 1 < len(headers) else len(text)]
        # 只取本条自己的字段，别把下一节标题后的内容吞进来
        body = re.split(r"^#{2,4}\s", body, maxsplit=1, flags=re.M)[0]

        # `L2 · 环境与交互` / `元 · 评测集` / `L3 · 记忆 · 环境与交互`（双柱只在第一个 · 上切）
        # 没有分隔符时 pillar 留空，让调用侧的校验报出来——不要兜底成 layer，
        # 那会把「文档格式变了」伪装成一条正常数据。
        layer, _, pillar = layer_pillar.partition(" · ")
        row = {"code": f"{group_code}-{seq}", "group_code": group_code,
               "group_name": groups.get(group_code, ""), "name": name.strip(),
               "layer": layer.strip(), "pillar": pillar.strip()}
        row.update({c: "" for c in TEXT_COLUMNS})
        for f in FIELD_RE.finditer(body):
            label, value = f.group(1).strip(), f.group(2).strip()
            column = _column_for(label)
            # 同一列命中多次（陷阱一/陷阱二、多条 notes）就接着追加，别互相覆盖；
            # notes 保留原标签，否则读的人不知道这段是「实测量级」还是「量级参考」。
            piece = f"{label}：{value}" if column == "notes" else value
            row[column] = f"{row[column]}\n{piece}" if row[column] else piece
        rows.append(row)
    return rows


def sync_metrics(db: Session, rows: list[dict]) -> dict:
    """按 code 幂等 upsert。返回 {added, updated, unchanged, stale}。

    stale 是「库里有、文档里没有」的编号，只报不删：指标下线是需要人确认的动作，
    静默删除会连带 evaluators.metric_code 变成悬空引用。
    """
    existing = {m.code: m for m in db.query(models.Metric).all()}
    fields = ["group_code", "group_name", "name", "layer", "pillar", *TEXT_COLUMNS]
    added = updated = unchanged = 0

    for row in rows:
        cur = existing.get(row["code"])
        if cur is None:
            db.add(models.Metric(**row))
            added += 1
            continue
        changed = [f for f in fields if getattr(cur, f) != row[f]]
        if changed:
            for f in changed:
                setattr(cur, f, row[f])
            updated += 1
        else:
            unchanged += 1

    stale = sorted(set(existing) - {r["code"] for r in rows})
    db.commit()
    return {"added": added, "updated": updated, "unchanged": unchanged, "stale": stale}


def coverage(db: Session, workspace_id: str | None = None) -> dict:
    """「层 × 柱」覆盖度：每格 已挂评估器的指标数 / 该格指标总数。

    指标库是全局字典，评估器却按工作空间隔离——所以覆盖度必须按空间算，
    否则 A 团队会看到 B 团队的评估器把格子填满了。不传 workspace_id 才是全局口径。
    """
    metrics = db.query(models.Metric).all()
    q = db.query(models.Evaluator.metric_code).filter(models.Evaluator.metric_code.isnot(None))
    if workspace_id:
        q = q.filter(models.Evaluator.workspace_id == workspace_id)
    mapped = {c for (c,) in q.distinct()}

    cells: dict[tuple[str, str], dict] = {}
    for m in metrics:
        cell = cells.setdefault((m.layer, m.pillar), {"total": 0, "done": 0})
        cell["total"] += 1
        if m.code in mapped:
            cell["done"] += 1

    return {
        "layers": sorted({m.layer for m in metrics}),
        "pillars": sorted({m.pillar for m in metrics}),
        "cells": [{"layer": l, "pillar": p, **v} for (l, p), v in sorted(cells.items())],
        "total": len(metrics),
        "done": sum(1 for m in metrics if m.code in mapped),
    }
