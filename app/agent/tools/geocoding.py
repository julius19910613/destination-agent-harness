"""Geocoding tool for converting addresses to coordinates."""
from typing import Dict, Any, Optional
import logging
import aiohttp
from app.monitoring.metrics import track_tool_metrics

logger = logging.getLogger(__name__)


class GeocodingTool:
    """Geocoding tool using Nominatim (OpenStreetMap) API."""

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    @property
    def name(self) -> str:
        """Tool name."""
        return "geocode"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Convert address/destination to latitude and longitude coordinates"

    @track_tool_metrics('geocode')
    async def execute(
        self,
        address: str,
        country: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Geocode an address to coordinates.

        Args:
            address: Address or destination name.
            country: Optional country hint.

        Returns:
            {
                "lat": float or None,
                "lng": float or None,
                "formatted_address": str or None,
                "confidence": float
            }
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "q": f"{address}, {country}" if country else address,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1
                }

                headers = {
                    "User-Agent": "DestinationAgent/1.0"
                }

                async with session.get(
                    self.BASE_URL,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Geocoding API error: {response.status}")
                        return {
                            "lat": None,
                            "lng": None,
                            "formatted_address": None,
                            "confidence": 0.0
                        }

                    data = await response.json()

                    if not data:
                        logger.warning(f"No geocoding results for: {address}")
                        return {
                            "lat": None,
                            "lng": None,
                            "formatted_address": None,
                            "confidence": 0.0
                        }

                    result = data[0]
                    lat = float(result["lat"])
                    lng = float(result["lon"])
                    formatted = result.get("display_name", address)

                    logger.info(f"Geocoded {address} -> ({lat}, {lng})")

                    return {
                        "lat": lat,
                        "lng": lng,
                        "formatted_address": formatted,
                        "confidence": 0.9
                    }

        except aiohttp.ClientError as e:
            logger.error(f"Geocoding network error: {e}")
            return {
                "lat": None,
                "lng": None,
                "formatted_address": None,
                "confidence": 0.0
            }
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            return {
                "lat": None,
                "lng": None,
                "formatted_address": None,
                "confidence": 0.0
            }

    async def reverse_geocode(
        self,
        lat: float,
        lng: float
    ) -> Dict[str, Any]:
        """
        Reverse geocode coordinates to address.

        Args:
            lat: Latitude.
            lng: Longitude.

        Returns:
            {
                "address": str or None,
                "city": str or None,
                "country": str or None
            }
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://nominatim.openstreetmap.org/reverse"
                params = {
                    "lat": lat,
                    "lon": lng,
                    "format": "json",
                    "addressdetails": 1
                }

                headers = {
                    "User-Agent": "DestinationAgent/1.0"
                }

                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Reverse geocoding API error: {response.status}")
                        return {
                            "address": None,
                            "city": None,
                            "country": None
                        }

                    data = await response.json()

                    if "error" in data:
                        logger.warning(f"Reverse geocoding error: {data['error']}")
                        return {
                            "address": None,
                            "city": None,
                            "country": None
                        }

                    address = data.get("display_name")
                    address_details = data.get("address", {})
                    city = address_details.get("city") or address_details.get("town")
                    country = address_details.get("country")

                    logger.info(f"Reverse geocoded ({lat}, {lng}) -> {city}, {country}")

                    return {
                        "address": address,
                        "city": city,
                        "country": country
                    }

        except Exception as e:
            logger.error(f"Reverse geocoding failed: {e}")
            return {
                "address": None,
                "city": None,
                "country": None
            }
