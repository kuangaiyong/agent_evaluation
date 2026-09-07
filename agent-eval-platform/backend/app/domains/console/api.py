from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.db import get_db
from ..identity.deps import current_workspace
from .service import dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("")
def get_dashboard(ws=Depends(current_workspace), db: Session = Depends(get_db),
                  range: str = "7d", app_id: str = ""):
    return dashboard(db, ws["id"], range, app_id)
