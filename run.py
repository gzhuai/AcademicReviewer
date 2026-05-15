import uvicorn
from app.config import settings, ensure_dirs

if __name__ == "__main__":
    ensure_dirs()
    from app.database import init_db
    init_db()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
