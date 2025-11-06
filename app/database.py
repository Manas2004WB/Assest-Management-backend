from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import URL

Base = declarative_base()

connection_string = (
    "Driver=ODBC Driver 17 for SQL Server;"
    "Server=WB-PF485SZV\\SQLEXPRESS;"
    "Database=Asset Hierarchy;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

DATABASE_URL = URL.create(
    "mssql+pyodbc", query={"odbc_connect": connection_string}
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test"))
            print("Database connected successfully:", result.scalar())
    except Exception as e:
        print("Database connection failed:", e)

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    test_connection()
