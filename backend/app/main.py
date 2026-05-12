from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import artifacts, images, reconstruct, stories, kg, rag

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize services (optional, will connect if available)
    await init_optional_services()

    logger.info("All services started")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    await shutdown_services()


async def init_optional_services():
    """初始化可选服务 (Neo4j, Milvus)"""
    # Neo4j
    try:
        from app.services.kg_service import get_kg_service
        kg_service = get_kg_service()
        if kg_service.connect():
            logger.info("Neo4j connected")
        else:
            logger.warning("Neo4j not available - knowledge graph features disabled")
    except Exception as e:
        logger.warning(f"Neo4j initialization skipped: {e}")

    # Milvus
    try:
        from app.services.rag_service import get_rag_service
        rag_service = get_rag_service()
        if rag_service.connect():
            logger.info("Milvus connected")
        else:
            logger.warning("Milvus not available - RAG features disabled")
    except Exception as e:
        logger.warning(f"Milvus initialization skipped: {e}")


async def shutdown_services():
    """关闭服务"""
    # Disconnect Neo4j
    try:
        from app.services.kg_service import get_kg_service
        kg_service = get_kg_service()
        kg_service.disconnect()
        logger.info("Neo4j disconnected")
    except Exception:
        pass

    # Disconnect Milvus
    try:
        from app.services.rag_service import get_rag_service
        rag_service = get_rag_service()
        rag_service.disconnect()
        logger.info("Milvus disconnected")
    except Exception:
        pass

    # Unload AI models
    try:
        from app.services.gemma_service import unload_gemma_model
        unload_gemma_model()
        logger.info("Gemma model unloaded")
    except Exception:
        pass

    try:
        from app.services.hunyuan3d_service import unload_hunyuan3d_model
        unload_hunyuan3d_model()
        logger.info("Hunyuan3D model unloaded")
    except Exception:
        pass


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="启物博言智慧博物馆系统 - 让文物活起来",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploads
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "raw", "artifacts")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Include API routers
app.include_router(artifacts.router, prefix=settings.api_prefix, tags=["artifacts"])
app.include_router(images.router, prefix=settings.api_prefix, tags=["images"])
app.include_router(reconstruct.router, prefix=settings.api_prefix, tags=["reconstruct"])
app.include_router(stories.router, prefix=settings.api_prefix, tags=["stories"])
app.include_router(kg.router, prefix=settings.api_prefix, tags=["knowledge-graph"])
app.include_router(rag.router, prefix=settings.api_prefix, tags=["rag"])


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "disabled",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.app_version,
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查，包含各服务状态"""
    health = {
        "status": "healthy",
        "version": settings.app_version,
        "services": {},
    }

    # Check Neo4j
    try:
        from app.services.kg_service import get_kg_service
        kg_service = get_kg_service()
        if kg_service._connected:
            health["services"]["neo4j"] = {"status": "connected"}
        else:
            if kg_service.connect():
                health["services"]["neo4j"] = {"status": "connected"}
            else:
                health["services"]["neo4j"] = {"status": "disconnected"}
    except Exception as e:
        health["services"]["neo4j"] = {"status": "error", "message": str(e)}

    # Check Milvus
    try:
        from app.services.rag_service import get_rag_service
        rag_service = get_rag_service()
        if rag_service._connected:
            health["services"]["milvus"] = {"status": "connected"}
        else:
            if rag_service.connect():
                health["services"]["milvus"] = {"status": "connected"}
            else:
                health["services"]["milvus"] = {"status": "disconnected"}
    except Exception as e:
        health["services"]["milvus"] = {"status": "error", "message": str(e)}

    # Check Gemma
    try:
        from app.services.gemma_service import get_gemma_service
        gemma_service = get_gemma_service()
        health["services"]["gemma"] = {
            "status": "loaded" if gemma_service._loaded else "not_loaded",
            "model": settings.gemma_model_name,
        }
    except Exception as e:
        health["services"]["gemma"] = {"status": "error", "message": str(e)}

    # Check Hunyuan3D
    try:
        from app.services.hunyuan3d_service import get_hunyuan3d_service
        hunyuan_service = get_hunyuan3d_service()
        health["services"]["hunyuan3d"] = {
            "status": "loaded" if hunyuan_service._loaded else "not_loaded",
            "model": settings.hunyuan3d_repo_id,
        }
    except Exception as e:
        health["services"]["hunyuan3d"] = {"status": "error", "message": str(e)}

    return health


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
