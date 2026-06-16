from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.core.config import load_settings

settings = load_settings()

# Engine padrao
engine = create_engine(
    settings.database_url, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Sessao SQLAlchemy padrao (Sincrona por enquanto)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para criar os modelos novos futuramente ou referenciar os existentes
Base = declarative_base()

# Dependencia FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
