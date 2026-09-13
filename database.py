from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase , sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

#Creating a engine 
engine = create_engine( 
    url= SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread":False}, #Default sqlite restricted to one thread this para remove restriction
)

#Making a session 
SessionLocal = sessionmaker(autocommit = False , autoflush= False , bind=engine)

class Base(DeclarativeBase):
    pass

def get_db(): # It is a generator and it  return a db object  
    with SessionLocal() as db:
        yield db

