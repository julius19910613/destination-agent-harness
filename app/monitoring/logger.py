"""Structured logging for monitoring and audit."""
import logging
import json
import time
from typing import Dict, Any, Optional


class StructuredLogger:
    """Structured JSON logger for Harness monitoring."""

    def __init__(self, name: str):
        """
        Initialize structured logger.

        Args:
            name: Logger name.
        """
        self.logger = logging.getLogger(name)

    def log_request(
        self,
        request_id: str,
        endpoint: str,
        input_data: Dict[str, Any],
        metadata: Optional[Dict] = None
    ):
        """
        Log request started.

        Args:
            request_id: Unique request identifier.
            endpoint: API endpoint.
            input_data: Input data dictionary.
            metadata: Optional metadata.
        """
        log_entry = {
            "event": "request_started",
            "request_id": request_id,
            "endpoint": endpoint,
            "input": input_data,
            "timestamp": time.time()
        }

        if metadata:
            log_entry["metadata"] = metadata

        self.logger.info(json.dumps(log_entry))

    def log_response(
        self,
        request_id: str,
        response_data: Dict[str, Any],
        duration_ms: float,
        success: bool = True
    ):
        """
        Log request completed.

        Args:
            request_id: Unique request identifier.
            response_data: Response data dictionary.
            duration_ms: Request duration in milliseconds.
            success: Whether request succeeded.
        """
        self.logger.info(json.dumps({
            "event": "request_completed",
            "request_id": request_id,
            "response": response_data,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "timestamp": time.time()
        }))

    def log_error(
        self,
        request_id: str,
        error: Exception,
        context: Optional[Dict] = None
    ):
        """
        Log request failed.

        Args:
            request_id: Unique request identifier.
            error: Exception that occurred.
            context: Optional context dictionary.
        """
        self.logger.error(json.dumps({
            "event": "request_failed",
            "request_id": request_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "timestamp": time.time()
        }))

    def log_tool_usage(
        self,
        request_id: str,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: float
    ):
        """
        Log tool execution.

        Args:
            request_id: Unique request identifier.
            tool_name: Name of the tool.
            input_data: Tool input data.
            output_data: Tool output data.
            duration_ms: Tool execution duration in milliseconds.
        """
        self.logger.info(json.dumps({
            "event": "tool_executed",
            "request_id": request_id,
            "tool": tool_name,
            "input": input_data,
            "output": output_data,
            "duration_ms": round(duration_ms, 2),
            "timestamp": time.time()
        }))
