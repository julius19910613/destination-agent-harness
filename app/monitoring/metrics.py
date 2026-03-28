"""Prometheus metrics for monitoring."""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable
import logging

logger = logging.getLogger(__name__)

# Request metrics
REQUEST_COUNT = Counter(
    'destination_agent_requests_total',
    'Total number of requests',
    ['endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'destination_agent_request_duration_seconds',
    'Request latency in seconds',
    ['endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

# Cache metrics
CACHE_HITS = Counter(
    'destination_agent_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'destination_agent_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Tool usage metrics
TOOL_USAGE = Counter(
    'destination_agent_tool_usage_total',
    'Total tool usage count',
    ['tool_name', 'status']
)

TOOL_LATENCY = Histogram(
    'destination_agent_tool_duration_seconds',
    'Tool execution duration in seconds',
    ['tool_name'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Gemini API metrics
GEMINI_API_CALLS = Counter(
    'destination_agent_gemini_api_calls_total',
    'Total Gemini API calls',
    ['status']
)

GEMINI_API_LATENCY = Histogram(
    'destination_agent_gemini_api_duration_seconds',
    'Gemini API call duration in seconds',
    buckets=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0]
)

# Active requests gauge
ACTIVE_REQUESTS = Gauge(
    'destination_agent_active_requests',
    'Number of active requests'
)

# Agent info
AGENT_INFO = Info(
    'destination_agent',
    'Agent information'
)
AGENT_INFO.info({
    'version': '1.0.0',
    'model': 'gemini-3.1-flash-lite-preview',
    'phase': 'harness-2'
})


def track_request_metrics(endpoint: str):
    """
    Decorator to track request metrics.
    
    Args:
        endpoint: Endpoint name (e.g., 'extract_destination')
    
    Usage:
        @track_request_metrics('extract_destination')
        async def extract_destination(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ACTIVE_REQUESTS.inc()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(endpoint=endpoint, status="success").inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(endpoint=endpoint, status="error").inc()
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
                ACTIVE_REQUESTS.dec()
        
        return wrapper
    return decorator


def track_tool_metrics(tool_name: str):
    """
    Decorator to track tool execution metrics.
    
    Args:
        tool_name: Tool name (e.g., 'language_detector')
    
    Usage:
        @track_tool_metrics('language_detector')
        async def execute(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                TOOL_USAGE.labels(tool_name=tool_name, status="success").inc()
                return result
            except Exception as e:
                TOOL_USAGE.labels(tool_name=tool_name, status="error").inc()
                logger.error(f"Tool {tool_name} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                TOOL_LATENCY.labels(tool_name=tool_name).observe(duration)
        
        return wrapper
    return decorator
