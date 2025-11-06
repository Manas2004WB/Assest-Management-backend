from sqlalchemy import text
from app.database import engine
from fastapi import FastAPI
from app.database import engine, Base
from app.routes import node_routes

app = FastAPI(title="Asset Hierarchy API")

Base.metadata.create_all(bind=engine)
app.include_router(node_routes.router, prefix="/api", tags=["Nodes"])

@app.get("/db-test")
def test_db_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test"))
            return {"status": "success", "message": "Database connected", "value": result.scalar()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
