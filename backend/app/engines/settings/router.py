import logging

from fastapi import APIRouter, Body

from app.database import get_connection, close_connection
from app.config import settings as app_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("")
def get_settings():
    conn = get_connection(app_settings.database_path)
    try:
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
        return {row[0]: row[1] for row in rows}
    finally:
        close_connection(app_settings.database_path)


@router.put("")
def update_settings(updates: dict[str, str] = Body(...)):
    conn = get_connection(app_settings.database_path)
    try:
        for key, value in updates.items():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = ?",
                (key, value, value),
            )
        return {"status": "ok", "updated": list(updates.keys())}
    finally:
        close_connection(app_settings.database_path)
