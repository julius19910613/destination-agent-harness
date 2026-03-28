"""Address validation tool."""
from typing import Dict, Any, Optional
import logging
import aiohttp
from app.monitoring.metrics import track_tool_metrics

logger = logging.getLogger(__name__)


class AddressValidatorTool:
    """Address validation tool using local database or external API."""

    # Local database of known destinations
    KNOWN_DESTINATIONS = {
        # 中文城市
        "北京": {"country": "中国", "continent": "亚洲", "type": "city", "aliases": ["Beijing", "Peking"]},
        "上海": {"country": "中国", "continent": "亚洲", "type": "city", "aliases": ["Shanghai"]},
        "广州": {"country": "中国", "continent": "亚洲", "type": "city", "aliases": ["Guangzhou", "Canton"]},
        "深圳": {"country": "中国", "continent": "亚洲", "type": "city", "aliases": ["Shenzhen"]},
        "香港": {"country": "中国", "continent": "亚洲", "type": "city", "aliases": ["Hong Kong", "HK"]},
        "台北": {"country": "中国台湾", "continent": "亚洲", "type": "city", "aliases": ["Taipei", "Taiwan"]},
        
        # 亚洲主要城市
        "东京": {"country": "日本", "continent": "亚洲", "type": "city", "aliases": ["Tokyo", "とうきょう"]},
        "大阪": {"country": "日本", "continent": "亚洲", "type": "city", "aliases": ["Osaka", "おおさか"]},
        "京都": {"country": "日本", "continent": "亚洲", "type": "city", "aliases": ["Kyoto", "きょうと"]},
        "首尔": {"country": "韩国", "continent": "亚洲", "type": "city", "aliases": ["Seoul", "서울"]},
        "新加坡": {"country": "新加坡", "continent": "亚洲", "type": "city", "aliases": ["Singapore", "SG"]},
        "曼谷": {"country": "泰国", "continent": "亚洲", "type": "city", "aliases": ["Bangkok", "กรุงเทพ"]},
        "吉隆坡": {"country": "马来西亚", "continent": "亚洲", "type": "city", "aliases": ["Kuala Lumpur", "KL"]},
        
        # 欧洲主要城市
        "巴黎": {"country": "法国", "continent": "欧洲", "type": "city", "aliases": ["Paris", "パリ"]},
        "伦敦": {"country": "英国", "continent": "欧洲", "type": "city", "aliases": ["London", "Londres"]},
        "柏林": {"country": "德国", "continent": "欧洲", "type": "city", "aliases": ["Berlin"]},
        "罗马": {"country": "意大利", "continent": "欧洲", "type": "city", "aliases": ["Rome", "Roma"]},
        "马德里": {"country": "西班牙", "continent": "欧洲", "type": "city", "aliases": ["Madrid"]},
        "阿姆斯特丹": {"country": "荷兰", "continent": "欧洲", "type": "city", "aliases": ["Amsterdam"]},
        "维也纳": {"country": "奥地利", "continent": "欧洲", "type": "city", "aliases": ["Vienna", "Wien"]},
        "苏黎世": {"country": "瑞士", "continent": "欧洲", "type": "city", "aliases": ["Zurich", "Zürich"]},
        
        # 北美主要城市
        "纽约": {"country": "美国", "continent": "北美洲", "type": "city", "aliases": ["New York", "NYC", "NY"]},
        "洛杉矶": {"country": "美国", "continent": "北美洲", "type": "city", "aliases": ["Los Angeles", "LA"]},
        "旧金山": {"country": "美国", "continent": "北美洲", "type": "city", "aliases": ["San Francisco", "SF"]},
        "芝加哥": {"country": "美国", "continent": "北美洲", "type": "city", "aliases": ["Chicago"]},
        "多伦多": {"country": "加拿大", "continent": "北美洲", "type": "city", "aliases": ["Toronto"]},
        "温哥华": {"country": "加拿大", "continent": "北美洲", "type": "city", "aliases": ["Vancouver"]},
        
        # 大洋洲主要城市
        "悉尼": {"country": "澳大利亚", "continent": "大洋洲", "type": "city", "aliases": ["Sydney"]},
        "墨尔本": {"country": "澳大利亚", "continent": "大洋洲", "type": "city", "aliases": ["Melbourne"]},
        "奥克兰": {"country": "新西兰", "continent": "大洋洲", "type": "city", "aliases": ["Auckland"]},
        
        # 中东主要城市
        "迪拜": {"country": "阿联酋", "continent": "亚洲", "type": "city", "aliases": ["Dubai"]},
        "伊斯坦布尔": {"country": "土耳其", "continent": "欧洲", "type": "city", "aliases": ["Istanbul"]},
        
        # 非洲主要城市
        "开罗": {"country": "埃及", "continent": "非洲", "type": "city", "aliases": ["Cairo"]},
        "开普敦": {"country": "南非", "continent": "非洲", "type": "city", "aliases": ["Cape Town"]},
    }

    @property
    def name(self) -> str:
        """Tool name."""
        return "validate_address"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Validate if an address/destination is real and get metadata"

    @track_tool_metrics('validate_address')
    async def execute(
        self,
        destination: str,
        country: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Validate destination and get metadata.

        Args:
            destination: Destination name to validate.
            country: Optional country hint.

        Returns:
            {
                "is_valid": bool,
                "country": str or None,
                "continent": str or None,
                "type": str or None,
                "confidence": float
            }
        """
        # Check exact match
        if destination in self.KNOWN_DESTINATIONS:
            info = self.KNOWN_DESTINATIONS[destination]
            logger.info(f"Address validated (exact match): {destination}")
            return {
                "is_valid": True,
                "country": info["country"],
                "continent": info["continent"],
                "type": info["type"],
                "confidence": 1.0
            }

        # Check aliases
        for dest, info in self.KNOWN_DESTINATIONS.items():
            if destination.lower() in [alias.lower() for alias in info.get("aliases", [])]:
                logger.info(f"Address validated (alias match): {destination} -> {dest}")
                return {
                    "is_valid": True,
                    "country": info["country"],
                    "continent": info["continent"],
                    "type": info["type"],
                    "confidence": 0.95,
                    "canonical_name": dest
                }

        # If country hint provided, check if it matches
        if country:
            for dest, info in self.KNOWN_DESTINATIONS.items():
                if info["country"] == country and destination.lower() in dest.lower():
                    logger.info(f"Address validated (country hint): {destination} -> {dest}")
                    return {
                        "is_valid": True,
                        "country": info["country"],
                        "continent": info["continent"],
                        "type": info["type"],
                        "confidence": 0.8,
                        "canonical_name": dest
                    }

        # Not found
        logger.warning(f"Address validation failed: {destination}")
        return {
            "is_valid": False,
            "country": None,
            "continent": None,
            "type": None,
            "confidence": 0.0
        }

    def get_suggestions(self, query: str, limit: int = 5) -> list[str]:
        """
        Get destination suggestions based on partial match.

        Args:
            query: Partial destination name.
            limit: Maximum number of suggestions.

        Returns:
            List of suggested destinations.
        """
        suggestions = []
        query_lower = query.lower()

        # Check main names
        for dest in self.KNOWN_DESTINATIONS.keys():
            if query_lower in dest.lower():
                suggestions.append(dest)

        # Check aliases
        for dest, info in self.KNOWN_DESTINATIONS.items():
            for alias in info.get("aliases", []):
                if query_lower in alias.lower() and dest not in suggestions:
                    suggestions.append(dest)

        return suggestions[:limit]
