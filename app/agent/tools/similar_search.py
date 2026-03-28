"""Similar destination search tool."""
from typing import Dict, Any, List
import logging
from difflib import SequenceMatcher
from app.monitoring.metrics import track_tool_metrics

logger = logging.getLogger(__name__)


class SimilarSearchTool:
    """Tool for finding similar destinations based on fuzzy matching."""

    def __init__(self):
        """Initialize with address validator for destination database."""
        from app.agent.tools.address_validator import AddressValidatorTool
        self.address_validator = AddressValidatorTool()

    @property
    def name(self) -> str:
        """Tool name."""
        return "search_similar"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Search for similar destinations based on fuzzy matching"

    @track_tool_metrics('search_similar')
    async def execute(
        self,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search for similar destinations.

        Args:
            query: Search query.
            limit: Maximum number of results.
            min_similarity: Minimum similarity score (0.0 to 1.0).

        Returns:
            {
                "results": [
                    {
                        "name": str,
                        "country": str,
                        "similarity": float
                    }
                ],
                "total": int
            }
        """
        results = []
        query_lower = query.lower()

        # Search through known destinations
        for dest, info in self.address_validator.KNOWN_DESTINATIONS.items():
            # Calculate similarity with main name
            similarity = SequenceMatcher(None, query_lower, dest.lower()).ratio()

            # Also check aliases
            for alias in info.get("aliases", []):
                alias_similarity = SequenceMatcher(
                    None, query_lower, alias.lower()
                ).ratio()
                similarity = max(similarity, alias_similarity)

            # If similarity is high enough, add to results
            if similarity >= min_similarity:
                results.append({
                    "name": dest,
                    "country": info["country"],
                    "continent": info["continent"],
                    "type": info["type"],
                    "similarity": round(similarity, 3)
                })

        # Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # Limit results
        results = results[:limit]

        logger.info(
            f"Similar search for '{query}': found {len(results)} results "
            f"(similarity >= {min_similarity})"
        )

        return {
            "results": results,
            "total": len(results),
            "query": query,
            "min_similarity": min_similarity
        }

    async def get_popular_destinations(
        self,
        country: str = None,
        continent: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get popular destinations, optionally filtered by country/continent.

        Args:
            country: Filter by country (optional).
            continent: Filter by continent (optional).
            limit: Maximum number of results.

        Returns:
            List of destinations.
        """
        results = []

        for dest, info in self.address_validator.KNOWN_DESTINATIONS.items():
            if country and info["country"] != country:
                continue
            if continent and info["continent"] != continent:
                continue

            results.append({
                "name": dest,
                "country": info["country"],
                "continent": info["continent"],
                "type": info["type"]
            })

            if len(results) >= limit:
                break

        return results

    async def get_continents(self) -> List[str]:
        """Get list of continents with destinations."""
        continents = set()
        for info in self.address_validator.KNOWN_DESTINATIONS.values():
            continents.add(info["continent"])
        return sorted(list(continents))

    async def get_countries(self, continent: str = None) -> List[str]:
        """
        Get list of countries with destinations.

        Args:
            continent: Filter by continent (optional).

        Returns:
            List of countries.
        """
        countries = set()
        for info in self.address_validator.KNOWN_DESTINATIONS.values():
            if continent and info["continent"] != continent:
                continue
            countries.add(info["country"])
        return sorted(list(countries))
