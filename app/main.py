from sqlalchemy import text
from app.database import engine
from fastapi import FastAPI
from app.database import engine, Base
from app.routes import node_routes
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_routes

app = FastAPI(title="Asset Hierarchy API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
app.include_router(node_routes.router, prefix="/api", tags=["Nodes"])
app.include_router(auth_routes.router, prefix="/api")

@app.get("/db-test")
def test_db_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test"))
            return {"status": "success", "message": "Database connected", "value": result.scalar()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
