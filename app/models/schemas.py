"""Pydantic schemas for the application."""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DestinationExtractionRequest(BaseModel):
    """Request model for destination extraction."""
    text: str = Field(..., min_length=1, description="User's natural language input")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate that text is not just whitespace."""
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()


class DestinationExtractionResponse(BaseModel):
    """Response model for destination extraction."""
    destination: str = Field(..., description="Extracted destination name")
    country: Optional[str] = Field(None, description="Country of the destination")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of the extraction (0.0 to 1.0)"
    )
    raw_text: str = Field(..., description="Original user input")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "destination": "巴黎",
                    "country": "法国",
                    "confidence": 0.95,
                    "raw_text": "我想去巴黎旅游"
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    model: Optional[str] = Field(None, description="AI model being used")
