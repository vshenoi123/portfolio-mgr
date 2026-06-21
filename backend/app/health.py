import time
import platform

_start_time: float = time.time()


def get_health() -> dict:
    from app.database import get_connection, close_connection
    from app.config import settings

    db_status = "error"
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "error"
    finally:
        try:
            close_connection()
        except Exception:
            pass

    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _start_time, 2),
        "python_version": platform.python_version(),
        "checks": {
            "database": db_status,
        },
    }