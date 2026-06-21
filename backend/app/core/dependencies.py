from fastapi import Request, HTTPException


def verify_api_key(request: Request) -> None:
    from app.config import settings
    if not settings.polygon_api_key:
        raise HTTPException(
            status_code=400,
            detail="Polygon API key not configured. Set POLYGON_API_KEY in .env",
        )
