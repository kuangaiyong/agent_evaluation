"""所有表的聚合入口。

各域的表定义在 domains/<域>/models.py，这里 re-export 以保持 `models.X` 的既有用法。
**更要紧的是**：只有把所有模型都 import 进来，Base.metadata 才收得全 ——
create_all 与 Alembic autogenerate 都依赖这一点，漏掉一个域就会静默少建表。
"""
from .shared.ids import uid  # noqa: F401
from .domains.identity.models import User, Workspace, Membership  # noqa: F401
from .domains.access.models import App  # noqa: F401
from .domains.observability.models import Trace  # noqa: F401
from .domains.evaluation.models import Metric, Evaluator, EvalTask, ScoreRecord, JudgeDailyStat  # noqa: F401
from .domains.dataset.models import Dataset, DatasetSample  # noqa: F401
from .domains.quality.models import BadCase, RegressionRun  # noqa: F401
from .domains.governance.models import AuditLog, Notification  # noqa: F401

__all__ = [
    "User",
    "Workspace",
    "Membership",
    "App",
    "Trace",
    "Metric",
    "Evaluator",
    "EvalTask",
    "ScoreRecord",
    "BadCase",
    "Dataset",
    "DatasetSample",
    "RegressionRun",
    "JudgeDailyStat",
    "AuditLog",
    "Notification",
    "uid",
]
