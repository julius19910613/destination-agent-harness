# Destination Agent Harness 设计文档

> 基于 Harness Engineering 最佳实践，为地址识别 agent 构建生产级基础设施

---

## 📋 目录

1. [架构概览](#架构概览)
2. [核心组件设计](#核心组件设计)
3. [实现路线图](#实现路线图)
4. [代码示例](#代码示例)

---

## 🏗️ 架构概览

### 当前架构（简单模式）
```
用户输入 → FastAPI → DestinationExtractor → Gemini API → 返回结果
```

### Harness 架构（生产级）
```
┌─────────────────────────────────────────────────────────────┐
│                      Destination Harness                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Input Guard  │  │ Rate Limiter │  │ Auth & AuthZ │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │          Context Manager (状态管理)               │      │
│  │  - Request History                                │      │
│  │  - User Preferences                               │      │
│  │  - Session State                                  │      │
│  └──────────────────────────────────────────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │            Tool Shed (工具集)                     │      │
│  │  ├─ Language Detector Agent                      │      │
│  │  ├─ Address Validator Agent                      │      │
│  │  ├─ Geocoding Agent (坐标转换)                    │      │
│  │  ├─ Cache Manager (缓存)                          │      │
│  │  └─ External API Client (外部API)                 │      │
│  └──────────────────────────────────────────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │         Destination Agent (核心智能体)            │      │
│  │  - System Prompt (增强版)                         │      │
│  │  - Multi-step Reasoning                          │      │
│  │  - Tool Orchestration                            │      │
│  └──────────────────────────────────────────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │          Output Guard & Verification             │      │
│  │  - Schema Validation                             │      │
│  │  - Confidence Check                              │      │
│  │  - Human Review (低置信度)                        │      │
│  └──────────────────────────────────────────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │         Monitoring & Audit (监控审计)             │      │
│  │  - Structured Logging                            │      │
│  │  - Metrics (Prometheus)                          │      │
│  │  - Error Tracking (Sentry)                       │      │
│  │  - Request Tracing                               │      │
│  └──────────────────────────────────────────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────┐      │
│  │         Error Recovery (错误恢复)                 │      │
│  │  - Retry with Backoff                            │      │
│  │  - Fallback Strategies                           │      │
│  │  - Circuit Breaker                               │      │
│  └──────────────────────────────────────────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 核心组件设计

### 1. System Prompt（增强版）

**当前问题**：
- 提示词较简单，缺乏工具使用指导
- 没有多步推理能力
- 缺乏错误处理指导

**改进方案**：
```python
HARNESS_SYSTEM_PROMPT = """你是一个专业的旅行目的地提取智能体，运行在一个结构化的 Harness 环境中。

## 你的能力
1. 从自然语言中提取目的地信息
2. 使用工具验证和增强提取结果
3. 多步推理处理复杂请求
4. 在不确定时请求帮助

## 可用工具
- `detect_language`: 检测输入语言
- `validate_address`: 验证地址是否真实存在
- `geocode`: 将地址转换为经纬度坐标
- `search_similar`: 搜索相似的目的地

## 工作流程
1. **理解阶段**：分析用户输入，识别语言和意图
2. **提取阶段**：提取目的地、国家、置信度
3. **验证阶段**：使用工具验证提取结果
4. **增强阶段**：如果置信度低，使用工具增强
5. **输出阶段**：返回结构化结果

## 决策规则
- 置信度 < 0.5：使用 `search_similar` 工具查找相似目的地
- 置信度 >= 0.5：直接返回结果
- 如果检测到歧义：返回多个候选结果

## 错误处理
- 如果工具调用失败：降级为基础提取
- 如果多次失败：返回低置信度结果并标记需要人工审核

输出格式必须是纯 JSON，遵循以下 schema：
{
  "destination": "string",
  "country": "string | null",
  "confidence": "float (0.0-1.0)",
  "language": "string (zh/en/ja/...)",
  "alternative_destinations": ["string"],
  "needs_review": "boolean",
  "metadata": {
    "validation_status": "string",
    "tools_used": ["string"],
    "reasoning_steps": ["string"]
  }
}
"""
```

---

### 2. Tools/MCPs（工具集）

#### 工具清单

| 工具名称 | 功能 | 优先级 | 实现难度 |
|---------|------|--------|---------|
| `detect_language` | 检测输入语言 | 高 | 低 |
| `validate_address` | 验证地址真实性 | 高 | 中 |
| `geocode` | 地址转坐标 | 中 | 中 |
| `search_similar` | 搜索相似地址 | 中 | 低 |
| `cache_manager` | 缓存管理 | 高 | 低 |

#### 工具接口设计

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseTool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    async def validate_input(self, **kwargs) -> bool:
        """验证输入"""
        return True


class LanguageDetectorTool(BaseTool):
    """语言检测工具"""
    
    @property
    def name(self) -> str:
        return "detect_language"
    
    @property
    def description(self) -> str:
        return "检测文本的语言（ISO 639-1 代码）"
    
    async def execute(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        执行语言检测
        
        Args:
            text: 待检测文本
        
        Returns:
            {
                "language": "zh",
                "confidence": 0.95,
                "alternatives": ["zh-CN", "zh-TW"]
            }
        """
        # 使用 langdetect 或 fasttext
        from langdetect import detect, LangDetectException
        
        try:
            lang = detect(text)
            return {
                "language": lang,
                "confidence": 0.9,
                "alternatives": []
            }
        except LangDetectException:
            return {
                "language": "unknown",
                "confidence": 0.0,
                "alternatives": []
            }


class AddressValidatorTool(BaseTool):
    """地址验证工具"""
    
    @property
    def name(self) -> str:
        return "validate_address"
    
    @property
    def description(self) -> str:
        return "验证地址是否真实存在"
    
    async def execute(self, destination: str, country: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        验证地址
        
        Args:
            destination: 目的地名称
            country: 国家名称（可选）
        
        Returns:
            {
                "is_valid": true,
                "country": "法国",
                "continent": "欧洲",
                "place_type": "city"
            }
        """
        # 使用外部 API（如 Google Places, OpenStreetMap Nominatim）
        # 或者使用本地数据库
        
        # 示例：简单的本地验证
        known_destinations = {
            "巴黎": {"country": "法国", "continent": "欧洲", "type": "city"},
            "东京": {"country": "日本", "continent": "亚洲", "type": "city"},
            "纽约": {"country": "美国", "continent": "北美洲", "type": "city"},
        }
        
        if destination in known_destinations:
            info = known_destinations[destination]
            return {
                "is_valid": True,
                "country": info["country"],
                "continent": info["continent"],
                "place_type": info["type"]
            }
        
        return {
            "is_valid": False,
            "country": None,
            "continent": None,
            "place_type": None
        }


class GeocodingTool(BaseTool):
    """地理编码工具"""
    
    @property
    def name(self) -> str:
        return "geocode"
    
    @property
    def description(self) -> str:
        return "将地址转换为经纬度坐标"
    
    async def execute(self, address: str, **kwargs) -> Dict[str, Any]:
        """
        地理编码
        
        Args:
            address: 地址字符串
        
        Returns:
            {
                "lat": 48.8566,
                "lng": 2.3522,
                "formatted_address": "Paris, France"
            }
        """
        # 使用 Nominatim (免费) 或 Google Geocoding API
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            url = f"https://nominatim.openstreetmap.org/search"
            params = {
                "q": address,
                "format": "json",
                "limit": 1
            }
            
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                
                if data:
                    return {
                        "lat": float(data[0]["lat"]),
                        "lng": float(data[0]["lon"]),
                        "formatted_address": data[0]["display_name"]
                    }
                
                return {
                    "lat": None,
                    "lng": None,
                    "formatted_address": None
                }


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, ttl: int = 3600):
        """
        Args:
            ttl: 缓存过期时间（秒）
        """
        self.cache = {}
        self.ttl = ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        import time
        
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        
        return None
    
    async def set(self, key: str, value: Any):
        """设置缓存"""
        import time
        self.cache[key] = (value, time.time())
```

---

### 3. Context Manager（上下文管理）

```python
from datetime import datetime
from typing import Dict, List, Optional
import json

class ContextManager:
    """上下文管理器"""
    
    def __init__(self, storage_backend: str = "memory"):
        """
        Args:
            storage_backend: 存储后端（memory/redis/sqlite）
        """
        self.storage_backend = storage_backend
        self.sessions: Dict[str, Dict] = {}
    
    async def get_session(self, session_id: str) -> Dict:
        """获取会话上下文"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": datetime.now(),
                "request_history": [],
                "user_preferences": {
                    "language": None,
                    "region": None
                },
                "state": {}
            }
        
        return self.sessions[session_id]
    
    async def add_request(
        self, 
        session_id: str, 
        request: str, 
        response: Dict
    ):
        """添加请求记录"""
        session = await self.get_session(session_id)
        session["request_history"].append({
            "timestamp": datetime.now(),
            "request": request,
            "response": response
        })
        
        # 限制历史记录长度
        if len(session["request_history"]) > 100:
            session["request_history"] = session["request_history"][-100:]
    
    async def update_preference(
        self, 
        session_id: str, 
        key: str, 
        value: Any
    ):
        """更新用户偏好"""
        session = await self.get_session(session_id)
        session["user_preferences"][key] = value
    
    async def set_state(
        self, 
        session_id: str, 
        key: str, 
        value: Any
    ):
        """设置状态"""
        session = await self.get_session(session_id)
        session["state"][key] = value
```

---

### 4. 监控和审计

```python
import logging
import time
from functools import wraps
from typing import Callable
import json

# 结构化日志
class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_request(
        self, 
        request_id: str, 
        endpoint: str, 
        input_data: Dict,
        metadata: Optional[Dict] = None
    ):
        """记录请求"""
        self.logger.info(
            json.dumps({
                "event": "request_started",
                "request_id": request_id,
                "endpoint": endpoint,
                "input": input_data,
                "metadata": metadata or {},
                "timestamp": time.time()
            })
        )
    
    def log_response(
        self, 
        request_id: str, 
        response_data: Dict,
        duration_ms: float,
        success: bool = True
    ):
        """记录响应"""
        self.logger.info(
            json.dumps({
                "event": "request_completed",
                "request_id": request_id,
                "response": response_data,
                "duration_ms": duration_ms,
                "success": success,
                "timestamp": time.time()
            })
        )
    
    def log_error(
        self, 
        request_id: str, 
        error: Exception,
        context: Optional[Dict] = None
    ):
        """记录错误"""
        self.logger.error(
            json.dumps({
                "event": "request_failed",
                "request_id": request_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
                "timestamp": time.time()
            })
        )
    
    def log_tool_usage(
        self, 
        request_id: str, 
        tool_name: str, 
        input_data: Dict,
        output_data: Dict,
        duration_ms: float
    ):
        """记录工具使用"""
        self.logger.info(
            json.dumps({
                "event": "tool_executed",
                "request_id": request_id,
                "tool": tool_name,
                "input": input_data,
                "output": output_data,
                "duration_ms": duration_ms,
                "timestamp": time.time()
            })
        )


# Prometheus 指标
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter(
    'destination_agent_requests_total',
    'Total number of requests',
    ['endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'destination_agent_request_duration_seconds',
    'Request latency in seconds',
    ['endpoint']
)

TOOL_USAGE = Counter(
    'destination_agent_tool_usage_total',
    'Total tool usage count',
    ['tool_name', 'status']
)

ACTIVE_REQUESTS = Gauge(
    'destination_agent_active_requests',
    'Number of active requests'
)


def track_metrics(endpoint: str):
    """装饰器：跟踪指标"""
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
```

---

### 5. 错误恢复

```python
import asyncio
from typing import Callable, Type, Optional
from functools import wraps

class RetryWithBackoff:
    """重试机制（指数退避）"""
    
    def __init__(
        self, 
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        """
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            exponential_base: 指数基数
            exceptions: 需要重试的异常类型
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.exceptions = exceptions
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_count = 0
            
            while retry_count < self.max_retries:
                try:
                    return await func(*args, **kwargs)
                except self.exceptions as e:
                    retry_count += 1
                    
                    if retry_count >= self.max_retries:
                        raise
                    
                    delay = min(
                        self.base_delay * (self.exponential_base ** retry_count),
                        self.max_delay
                    )
                    
                    logger.warning(
                        f"Retry {retry_count}/{self.max_retries} after {delay}s: {e}"
                    )
                    
                    await asyncio.sleep(delay)
            
            return await func(*args, **kwargs)
        
        return wrapper


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时（秒）
            expected_exception: 预期异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
                
                return result
            
            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                
                raise
        
        return wrapper
```

---

### 6. 安全防护

```python
from fastapi import HTTPException, Request
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
import re

# API Key 认证
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """验证 API Key"""
    valid_keys = os.getenv("VALID_API_KEYS", "").split(",")
    
    if api_key not in valid_keys:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    return api_key


# 速率限制
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/extract-destination")
@limiter.limit("10/minute")
async def extract_destination(
    request: Request,
    req: DestinationExtractionRequest,
    api_key: str = Depends(verify_api_key)
):
    # ... 处理逻辑
    pass


# 输入验证
class InputValidator:
    """输入验证器"""
    
    @staticmethod
    def validate_text(text: str) -> str:
        """验证输入文本"""
        # 长度限制
        if len(text) > 1000:
            raise ValueError("Text too long (max 1000 characters)")
        
        # 去除危险字符
        text = re.sub(r'<[^>]*>', '', text)  # 移除 HTML 标签
        text = re.sub(r'[<>\"\'\\]', '', text)  # 移除特殊字符
        
        return text.strip()
    
    @staticmethod
    def detect_injection(text: str) -> bool:
        """检测注入攻击"""
        patterns = [
            r'(?i)(select|insert|update|delete|drop|create|alter)',
            r'(?i)(script|javascript|vbscript)',
            r'(?i)(eval|exec|system)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        
        return False
```

---

## 🗺️ 实现路线图

### Phase 1: 基础 Harness（1-2 天）✅ 优先
- [x] 增强系统提示词
- [ ] 添加基础工具（语言检测、地址验证）
- [ ] 实现缓存管理
- [ ] 添加结构化日志

### Phase 2: 监控和恢复（1-2 天）
- [ ] Prometheus 指标
- [ ] 错误追踪（Sentry）
- [ ] 重试机制
- [ ] 熔断器

### Phase 3: 高级工具（2-3 天）
- [ ] 地理编码工具
- [ ] 相似地址搜索
- [ ] 外部 API 集成（Google Places）

### Phase 4: 上下文管理（1-2 天）
- [ ] 会话管理
- [ ] 请求历史
- [ ] 用户偏好

### Phase 5: 安全防护（1 天）
- [ ] API Key 认证
- [ ] 速率限制
- [ ] 输入验证

### Phase 6: 生产部署（1-2 天）
- [ ] Docker 容器化
- [ ] Kubernetes 部署
- [ ] 负载测试
- [ ] 文档完善

---

## 📊 预期效果

### 可靠性提升
- 错误率：从 5% 降低到 < 0.1%
- 平均响应时间：< 200ms
- P99 响应时间：< 500ms
- 可用性：99.9%

### 功能增强
- 支持 10+ 种语言
- 地址验证准确率 > 95%
- 缓存命中率 > 60%
- 自动错误恢复

### 可观测性
- 完整的请求追踪
- 实时监控仪表板
- 自动告警
- 审计日志

---

## 🔗 参考资料

- [The Anatomy of an Agent Harness - LangChain](https://blog.langchain.com/the-anatomy-of-an-agent-harness/)
- [Agent Harness in Agent Framework - Microsoft](https://devblogs.microsoft.com/agent-framework/)
- [Harness Engineering Complete Guide - NxCode](https://www.nxcode.io/resources/news/harness-engineering-complete-guide-ai-agent-codex-2026)

---

**下一步**：从 Phase 1 开始，逐步实现各个组件。需要我提供具体实现代码吗？
