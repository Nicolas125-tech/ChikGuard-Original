from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from src.core.config import load_settings

settings = load_settings()

# ---------------------------------------------------------
# 1. Conexão Síncrona (Para Threads/Background Workers)
# ---------------------------------------------------------
sync_url = settings.database_url
engine = create_engine(
    sync_url, 
    connect_args={"check_same_thread": False} if "sqlite" in sync_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------
# 2. Conexão Assíncrona (Para FastAPI Endpoints)
# ---------------------------------------------------------
# Converte a URL para o driver assíncrono correspondente
if "sqlite" in sync_url:
    async_url = sync_url.replace("sqlite://", "sqlite+aiosqlite://")
elif "postgresql" in sync_url:
    async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
else:
    async_url = sync_url

try:
    async_engine = create_async_engine(
        async_url,
        connect_args={"check_same_thread": False} if "sqlite" in async_url else {}
    )
    AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession)
except Exception:
    async_engine = None
    AsyncSessionLocal = None


# Base para os modelos
Base = declarative_base()

# Dependência FastAPI (Assíncrona - Padrão Moderno)
async def get_async_db():
    if AsyncSessionLocal is None:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
        return
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Dependência FastAPI Legada (Síncrona)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
