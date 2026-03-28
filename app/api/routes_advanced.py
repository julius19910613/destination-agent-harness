"""Advanced destination API routes (Phase 3)."""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.agent.tools.address_validator import AddressValidatorTool
from app.agent.tools.geocoding import GeocodingTool
from app.agent.tools.similar_search import SimilarSearchTool
from app.monitoring.metrics import track_request_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advanced", tags=["advanced-destination"])


# Request/Response models
class AddressValidationRequest(BaseModel):
    """Address validation request."""
    destination: str
    country: Optional[str] = None


class AddressValidationResponse(BaseModel):
    """Address validation response."""
    is_valid: bool
    country: Optional[str]
    continent: Optional[str]
    type: Optional[str]
    confidence: float
    canonical_name: Optional[str] = None


class GeocodingRequest(BaseModel):
    """Geocoding request."""
    address: str
    country: Optional[str] = None


class GeocodingResponse(BaseModel):
    """Geocoding response."""
    lat: Optional[float]
    lng: Optional[float]
    formatted_address: Optional[str]
    confidence: float


class SimilarSearchRequest(BaseModel):
    """Similar search request."""
    query: str
    limit: Optional[int] = 5
    min_similarity: Optional[float] = 0.5


class SimilarSearchResult(BaseModel):
    """Similar search result item."""
    name: str
    country: str
    continent: str
    type: str
    similarity: float


class SimilarSearchResponse(BaseModel):
    """Similar search response."""
    results: List[SimilarSearchResult]
    total: int
    query: str
    min_similarity: float


# API endpoints
@router.post(
    "/validate-address",
    response_model=AddressValidationResponse,
    summary="Validate address/destination",
    description="Validate if an address/destination is real and get metadata"
)
@track_request_metrics('validate_address')
async def validate_address(request: AddressValidationRequest):
    """Validate address and get metadata."""
    try:
        validator = AddressValidatorTool()
        result = await validator.execute(
            destination=request.destination,
            country=request.country
        )

        return AddressValidationResponse(**result)

    except Exception as e:
        logger.error(f"Address validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Address validation failed"
        )


@router.post(
    "/geocode",
    response_model=GeocodingResponse,
    summary="Geocode address",
    description="Convert address to latitude and longitude coordinates"
)
@track_request_metrics('geocode')
async def geocode_address(request: GeocodingRequest):
    """Geocode address to coordinates."""
    try:
        geocoder = GeocodingTool()
        result = await geocoder.execute(
            address=request.address,
            country=request.country
        )

        return GeocodingResponse(**result)

    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Geocoding failed"
        )


@router.post(
    "/search-similar",
    response_model=SimilarSearchResponse,
    summary="Search similar destinations",
    description="Find similar destinations based on fuzzy matching"
)
@track_request_metrics('search_similar')
async def search_similar(request: SimilarSearchRequest):
    """Search for similar destinations."""
    try:
        search_tool = SimilarSearchTool()
        result = await search_tool.execute(
            query=request.query,
            limit=request.limit,
            min_similarity=request.min_similarity
        )

        return SimilarSearchResponse(**result)

    except Exception as e:
        logger.error(f"Similar search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Similar search failed"
        )


@router.get(
    "/popular-destinations",
    summary="Get popular destinations",
    description="Get list of popular destinations, optionally filtered"
)
@track_request_metrics('get_popular_destinations')
async def get_popular_destinations(
    country: Optional[str] = Query(None, description="Filter by country"),
    continent: Optional[str] = Query(None, description="Filter by continent"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results")
):
    """Get popular destinations."""
    try:
        search_tool = SimilarSearchTool()
        results = await search_tool.get_popular_destinations(
            country=country,
            continent=continent,
            limit=limit
        )

        return {
            "results": results,
            "total": len(results),
            "filters": {
                "country": country,
                "continent": continent
            }
        }

    except Exception as e:
        logger.error(f"Failed to get popular destinations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get popular destinations"
        )


@router.get(
    "/continents",
    summary="Get continents",
    description="Get list of continents with destinations"
)
@track_request_metrics('get_continents')
async def get_continents():
    """Get list of continents."""
    try:
        search_tool = SimilarSearchTool()
        continents = await search_tool.get_continents()
        return {"continents": continents}

    except Exception as e:
        logger.error(f"Failed to get continents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get continents"
        )


@router.get(
    "/countries",
    summary="Get countries",
    description="Get list of countries with destinations"
)
@track_request_metrics('get_countries')
async def get_countries(continent: Optional[str] = Query(None)):
    """Get list of countries."""
    try:
        search_tool = SimilarSearchTool()
        countries = await search_tool.get_countries(continent=continent)
        return {
            "countries": countries,
            "continent_filter": continent
        }

    except Exception as e:
        logger.error(f"Failed to get countries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get countries"
        )
