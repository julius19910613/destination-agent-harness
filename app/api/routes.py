"""API routes for the destination extraction service."""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends, Request
from app.models.schemas import (
    DestinationExtractionRequest,
    DestinationExtractionResponse,
    ErrorResponse,
    HealthResponse,
)
from app.agent.destination_extractor import get_destination_extractor
from app.monitoring.metrics import track_request_metrics
from app.agent.gemini_client import get_gemini_client
from app.security.auth import security_check, InputValidator

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["destination-extraction"])


@router.post(
    "/extract-destination",
    response_model=DestinationExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract destination from natural language",
    description="Extract destination, country, and confidence from user's natural language input.",
    responses={
        200: {"description": "Successful extraction"},
        400: {"description": "Invalid input"},
        500: {"description": "Internal server error"},
    },
)
@track_request_metrics('extract_destination')
async def extract_destination(
    request: DestinationExtractionRequest,
    security: dict = Depends(security_check)
) -> DestinationExtractionResponse:
    """
    Extract destination information from natural language.

    Example:
        Input: {"text": "我想去巴黎旅游"}
        Output: {
            "destination": "巴黎",
            "country": "法国",
            "confidence": 0.95,
            "raw_text": "我想去巴黎旅游"
        }
    """
    try:
        # Validate input
        text = InputValidator.validate_text(request.text)
        
        # Check for injection
        if InputValidator.detect_injection(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input"
            )
        extractor = await get_destination_extractor()
        result = await extractor.extract_destination(request.text)
        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract destination. Please try again later.",
        )


@router.post(
    "/batch-extract-destinations",
    response_model=List[DestinationExtractionResponse],
    status_code=status.HTTP_200_OK,
    summary="Extract destinations from multiple texts",
    description="Extract destination information from multiple natural language inputs.",
)
@track_request_metrics('batch_extract_destinations')
async def batch_extract_destinations(requests: List[DestinationExtractionRequest]) -> List[DestinationExtractionResponse]:
    """
    Extract destinations from multiple texts.

    Example:
        Input: [{"text": "我想去巴黎"}, {"text": "计划去东京"}]
        Output: List of DestinationExtractionResponse
    """
    try:
        if not requests:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request list cannot be empty",
            )

        texts = [req.text for req in requests]
        extractor = await get_destination_extractor()
        results = await extractor.batch_extract_destinations(texts)
        return results

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error processing batch request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract destinations. Please try again later.",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the service and AI model are operational.",
)
async def health_check() -> HealthResponse:
    """
    Check the health of the service.

    Returns service status, version, and AI model information.
    """
    try:
        gemini_client = get_gemini_client()
        model_name = gemini_client.model if gemini_client.health_check() else "disconnected"

        return HealthResponse(
            status="ok",
            version="1.0.0",
            model=model_name,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="error",
            version="1.0.0",
            model="unknown",
        )


@router.get(
    "/",
    summary="API information",
    description="Get information about the destination extraction API.",
)
async def api_info() -> dict:
    """
    Get API information.

    Returns basic information about available endpoints.
    """
    return {
        "name": "Destination Extraction API",
        "version": "1.0.0",
        "description": "AI-powered destination extraction from natural language",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/extract-destination",
                "description": "Extract destination from a single text",
            },
            {
                "method": "POST",
                "path": "/api/batch-extract-destinations",
                "description": "Extract destinations from multiple texts",
            },
            {
                "method": "GET",
                "path": "/api/health",
                "description": "Health check endpoint",
            },
        ],
    }
