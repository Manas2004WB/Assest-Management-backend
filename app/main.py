from sqlalchemy import text
from app.database import engine
from fastapi import FastAPI
from app.database import engine, Base
from app.routes import node_routes
from fastapi.middleware.cors import CORSMiddleware

origins =["*"]
app = FastAPI(title="Asset Hierarchy API")
app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,  # Allow cookies to be sent with cross-origin requests
        allow_methods=["*"],     # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"],     # Allow all headers in the request
)


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
