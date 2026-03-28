"""Prometheus metrics endpoint."""
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns Prometheus-formatted metrics for monitoring.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/health/detailed")
async def detailed_health():
    """
    Detailed health check with component status.
    
    Returns health status of all components:
    - API
    - Gemini client
    - Cache
    - Tools
    """
    try:
        from app.agent.destination_extractor import get_destination_extractor
        from app.agent.gemini_client import get_gemini_client
        
        # Check Gemini client
        gemini_client = get_gemini_client()
        gemini_healthy = gemini_client.health_check()
        
        # Check cache (get_destination_extractor is now async)
        extractor = await get_destination_extractor()
        cache_stats = extractor.cache.get_stats()
        
        return {
            "status": "healthy" if gemini_healthy else "degraded",
            "version": "1.0.0",
            "components": {
                "api": {
                    "status": "healthy"
                },
                "gemini_client": {
                    "status": "healthy" if gemini_healthy else "unhealthy",
                    "model": gemini_client.model
                },
                "cache": {
                    "status": "healthy",
                    "stats": cache_stats
                }
            }
        }
    except Exception as e:
        import traceback
        return {
            "status": "unhealthy",
            "version": "1.0.0",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
