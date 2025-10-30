from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(
    title="Research Paper Assistant - RAG System",
    description="A production-ready RAG service that helps researchers efficiently query and understand academic papers",
    version="1.0.0"
)

# Include API routes
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)