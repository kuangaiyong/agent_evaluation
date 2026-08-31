"""把 01 分册的指标字典同步进 metrics 表。

    python -m scripts.sync_metrics [--file <01 分册路径>] [--dry-run]

默认路径按仓库结构推断（agent-eval-platform/backend/scripts → 仓库根 → 智能体评测体系/）。
幂等：重复跑只更新变化的行，不产生重复。文档删掉的指标只报 stale 不自动删——
指标下线要人确认，静默删会让 evaluators.metric_code 变成悬空引用。
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import SessionLocal, engine, Base, ensure_schema      # noqa: E402
from app.services.metric_dict import parse_dictionary, sync_metrics  # noqa: E402

DEFAULT_DOC = (pathlib.Path(__file__).resolve().parents[3]
               / "智能体评测体系" / "01-指标体系与指标字典.md")


def main() -> int:
    ap = argparse.ArgumentParser(description="同步指标字典到 metrics 表")
    ap.add_argument("--file", type=pathlib.Path, default=DEFAULT_DOC, help="01 分册 md 路径")
    ap.add_argument("--dry-run", action="store_true", help="只解析并打印，不写库")
    args = ap.parse_args()

    if not args.file.exists():
        print(f"找不到指标字典：{args.file}", file=sys.stderr)
        return 2

    rows = parse_dictionary(args.file.read_text(encoding="utf-8"))
    if not rows:
        print(f"解析出 0 条指标，检查文档格式是否变了：{args.file}", file=sys.stderr)
        return 1

    groups = {}
    for r in rows:
        groups.setdefault(r["group_code"], 0)
        groups[r["group_code"]] += 1
    print(f"解析 {args.file.name}：{len(rows)} 条指标 / {len(groups)} 组 "
          f"({', '.join(f'{k}:{v}' for k, v in sorted(groups.items()))})")

    # 先把「文档本身有问题」拦在写库之前：重复编号会撞主键，报 IntegrityError 没人看得懂
    seen, dup = set(), []
    for r in rows:
        (dup.append(r["code"]) if r["code"] in seen else seen.add(r["code"]))
    if dup:
        print(f"指标编号重复，先修文档再同步：{', '.join(sorted(set(dup)))}", file=sys.stderr)
        return 1

    for label, field in (("定义", "definition"), ("层", "layer"), ("柱", "pillar")):
        missing = [r["code"] for r in rows if not r[field]]
        if missing:
            print(f"⚠ {len(missing)} 条缺「{label}」：{', '.join(missing[:10])}", file=sys.stderr)

    if args.dry_run:
        for r in rows[:3]:
            print(f"  {r['code']} · {r['name']} ｜ {r['layer']} · {r['pillar']}")
        print("  …（--dry-run 未写库）")
        return 0

    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        stat = sync_metrics(db, rows)
    finally:
        db.close()

    print(f"写入完成：新增 {stat['added']} · 更新 {stat['updated']} · 未变 {stat['unchanged']}")
    if stat["stale"]:
        print(f"⚠ 库里有但文档已无（未自动删除，请人工确认）：{', '.join(stat['stale'])}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
