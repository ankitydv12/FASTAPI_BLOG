from sqlalchemy.ext.asyncio import create_async_engine , AsyncSession , async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

#Creating a engin
engine = create_async_engine(
    url= SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread":False}, #Default sqlite restricted to one thread this para remove restriction
)

#Making a session 
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False #
)

class Base(DeclarativeBase):
    pass

async def get_db(): # It is a generator and it  return a db object
    async with AsyncSessionLocal() as db:
        yield db

