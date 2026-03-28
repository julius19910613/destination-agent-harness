# Harness 快速开始指南

> 5 分钟上手，逐步为你的 agent 构建 Harness

---

## 🚀 Phase 1: 基础 Harness（立即可用）

### Step 1: 增强系统提示词（已完成）

你的提示词已经很完善了！建议微调：

```python
# 在 app/agent/prompts.py 中添加

HARNESS_SYSTEM_PROMPT = """你是一个专业的旅行目的地提取智能体，运行在 Harness 环境中。

## 工作流程
1. **理解**：分析用户输入，识别语言和意图
2. **提取**：提取目的地、国家、置信度
3. **验证**：（可选）验证提取结果
4. **输出**：返回结构化结果

## 决策规则
- 置信度 >= 0.7：直接返回
- 置信度 0.5-0.7：标记为 `needs_review: true`
- 置信度 < 0.5：返回 `destination: "unknown"`

## 输出格式
{
  "destination": "string",
  "country": "string | null",
  "confidence": "float (0.0-1.0)",
  "language": "string",
  "needs_review": "boolean"
}
"""
```

---

### Step 2: 添加语言检测工具（5 分钟）

```bash
# 安装依赖
cd /Users/ppt/projects/mcp_test
source venv/bin/activate
pip install langdetect
```

创建文件：`app/agent/tools/language_detector.py`

```python
"""语言检测工具"""
from langdetect import detect, LangDetectException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class LanguageDetectorTool:
    """语言检测工具"""
    
    @property
    def name(self) -> str:
        return "detect_language"
    
    @property
    def description(self) -> str:
        return "检测文本语言（ISO 639-1 代码）"
    
    async def execute(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        执行语言检测
        
        Args:
            text: 待检测文本
        
        Returns:
            {
                "language": "zh",
                "confidence": 0.9
            }
        """
        try:
            lang = detect(text)
            logger.info(f"Detected language: {lang} for text: {text[:50]}")
            
            return {
                "language": lang,
                "confidence": 0.9
            }
        
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
            return {
                "language": "unknown",
                "confidence": 0.0
            }
```

---

### Step 3: 添加缓存管理（5 分钟）

创建文件：`app/agent/tools/cache_manager.py`

```python
"""缓存管理器"""
import time
from typing import Any, Optional, Dict
import hashlib
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """简单的内存缓存"""
    
    def __init__(self, ttl: int = 3600):
        """
        Args:
            ttl: 缓存过期时间（秒），默认 1 小时
        """
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl
        logger.info(f"CacheManager initialized with TTL={ttl}s")
    
    def _generate_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def get(self, text: str) -> Optional[Any]:
        """获取缓存"""
        key = self._generate_key(text)
        
        if key in self.cache:
            value, timestamp = self.cache[key]
            
            # 检查是否过期
            if time.time() - timestamp < self.ttl:
                logger.info(f"Cache hit for key: {key[:8]}")
                return value
            else:
                # 过期，删除
                del self.cache[key]
                logger.info(f"Cache expired for key: {key[:8]}")
        
        return None
    
    async def set(self, text: str, value: Any):
        """设置缓存"""
        key = self._generate_key(text)
        self.cache[key] = (value, time.time())
        logger.info(f"Cache set for key: {key[:8]}")
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        return {
            "total_items": len(self.cache),
            "ttl": self.ttl
        }
```

---

### Step 4: 集成到 Agent（10 分钟）

修改文件：`app/agent/destination_extractor.py`

```python
"""Destination extraction agent using Google Gemini (with Harness)."""
import json
import logging
from typing import Optional, Dict, Any
from app.models.schemas import DestinationExtractionResponse
from app.agent.gemini_client import GeminiClient, get_gemini_client
from app.agent.prompts import build_destination_extraction_prompt
from app.agent.tools.language_detector import LanguageDetectorTool
from app.agent.tools.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class DestinationExtractor:
    """Agent for extracting destinations from natural language (with Harness)."""

    def __init__(self, client: Optional[GeminiClient] = None):
        """
        Initialize the destination extractor.

        Args:
            client: Optional Gemini client. If None, uses global instance.
        """
        self.client = client or get_gemini_client()
        
        # 初始化工具
        self.language_detector = LanguageDetectorTool()
        self.cache = CacheManager(ttl=3600)  # 1 小时缓存
        
        logger.info("DestinationExtractor initialized with Harness tools")

    async def extract_destination(self, text: str) -> DestinationExtractionResponse:
        """
        Extract destination information with Harness workflow.

        Args:
            text: User's natural language input.

        Returns:
            DestinationExtractionResponse with extracted destination info.
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        try:
            # Step 1: 检查缓存
            cached_result = await self.cache.get(text)
            if cached_result:
                logger.info(f"Returning cached result for: {text[:50]}")
                return cached_result

            # Step 2: 检测语言
            lang_result = await self.language_detector.execute(text)
            language = lang_result["language"]
            logger.info(f"Detected language: {language}")

            # Step 3: 提取目的地
            prompt = build_destination_extraction_prompt(text)
            response_text = await self.client.generate_json(prompt)

            # Step 4: 解析响应
            if response_text.startswith("```"):
                response_text = response_text.strip("```json").strip("```").strip()

            extraction_data = json.loads(response_text)

            # Step 5: 构建响应
            destination = extraction_data.get("destination", "unknown")
            country = extraction_data.get("country")
            confidence = float(extraction_data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            response = DestinationExtractionResponse(
                destination=destination,
                country=country,
                confidence=confidence,
                raw_text=text.strip(),
            )

            # Step 6: 缓存结果
            await self.cache.set(text, response)

            logger.info(
                f"Extracted destination: {destination} "
                f"(confidence: {confidence:.2f}, language: {language})"
            )

            return response

        except Exception as e:
            logger.error(f"Error extracting destination: {e}")
            raise

    async def batch_extract_destinations(
        self, texts: list[str]
    ) -> list[DestinationExtractionResponse]:
        """Extract destinations from multiple texts."""
        if not texts:
            raise ValueError("Cannot extract from empty text list")

        results = []
        for text in texts:
            try:
                result = await self.extract_destination(text)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract from text '{text}': {e}")
                results.append(
                    DestinationExtractionResponse(
                        destination="unknown",
                        country=None,
                        confidence=0.0,
                        raw_text=text,
                    )
                )

        return results


# Global extractor instance
_destination_extractor: Optional[DestinationExtractor] = None


def get_destination_extractor() -> DestinationExtractor:
    """Get or create the global destination extractor instance."""
    global _destination_extractor
    if _destination_extractor is None:
        _destination_extractor = DestinationExtractor()
    return _destination_extractor
```

---

### Step 5: 添加监控日志（5 分钟）

创建文件：`app/monitoring/logger.py`

```python
"""结构化日志记录"""
import logging
import json
import time
from typing import Dict, Any, Optional

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_request(
        self, 
        request_id: str, 
        endpoint: str, 
        input_data: Dict[str, Any],
        metadata: Optional[Dict] = None
    ):
        """记录请求"""
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
        """记录响应"""
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
        """记录错误"""
        self.logger.error(json.dumps({
            "event": "request_failed",
            "request_id": request_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "timestamp": time.time()
        }))
```

---

### Step 6: 测试 Harness（5 分钟）

创建测试文件：`tests/test_harness.py`

```python
"""Harness 功能测试"""
import pytest
from app.agent.destination_extractor import get_destination_extractor
from app.agent.tools.language_detector import LanguageDetectorTool
from app.agent.tools.cache_manager import CacheManager

@pytest.mark.asyncio
async def test_language_detection():
    """测试语言检测"""
    detector = LanguageDetectorTool()
    
    # 测试中文
    result = await detector.execute("我想去巴黎")
    assert result["language"] == "zh"
    assert result["confidence"] > 0
    
    # 测试英文
    result = await detector.execute("I want to go to Paris")
    assert result["language"] == "en"
    assert result["confidence"] > 0

@pytest.mark.asyncio
async def test_cache():
    """测试缓存"""
    cache = CacheManager(ttl=60)
    
    # 测试缓存写入和读取
    test_data = {"destination": "Paris", "country": "France"}
    await cache.set("test text", test_data)
    
    cached = await cache.get("test text")
    assert cached == test_data
    
    # 测试缓存未命中
    not_cached = await cache.get("nonexistent")
    assert not_cached is None

@pytest.mark.asyncio
async def test_extract_with_harness():
    """测试带 Harness 的提取"""
    extractor = get_destination_extractor()
    
    # 第一次调用（无缓存）
    result1 = await extractor.extract_destination("我想去巴黎旅游")
    assert result1.destination == "巴黎"
    assert result1.country == "法国"
    
    # 第二次调用（有缓存）
    result2 = await extractor.extract_destination("我想去巴黎旅游")
    assert result2.destination == "巴黎"
    assert result2 == result1  # 应该是完全相同的结果

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

运行测试：

```bash
cd /Users/ppt/projects/mcp_test
source venv/bin/activate
pytest tests/test_harness.py -v
```

---

## 📊 验证 Harness 是否工作

### 1. 检查日志输出

```bash
# 启动服务器（带日志）
python main.py

# 在另一个终端测试
curl -X POST http://localhost:8001/api/extract-destination \
  -H "Content-Type: application/json" \
  -d '{"text": "我想去巴黎旅游"}'
```

**预期日志**：
```json
{
  "event": "request_started",
  "request_id": "abc123",
  "endpoint": "/api/extract-destination",
  "input": {"text": "我想去巴黎旅游"}
}
{
  "event": "tool_executed",
  "tool": "detect_language",
  "output": {"language": "zh", "confidence": 0.9}
}
{
  "event": "request_completed",
  "response": {"destination": "巴黎", "country": "法国"},
  "duration_ms": 123.45
}
```

### 2. 测试缓存效果

```bash
# 第一次调用（慢）
time curl -X POST http://localhost:8001/api/extract-destination \
  -H "Content-Type: application/json" \
  -d '{"text": "我想去巴黎旅游"}'

# 第二次调用（快，有缓存）
time curl -X POST http://localhost:8001/api/extract-destination \
  -H "Content-Type: application/json" \
  -d '{"text": "我想去巴黎旅游"}'
```

**预期效果**：第二次调用应该快 50%+（因为命中缓存）

---

## 🎯 Phase 1 完成清单

- [ ] 增强系统提示词
- [ ] 添加语言检测工具
- [ ] 添加缓存管理
- [ ] 集成到 Agent
- [ ] 添加结构化日志
- [ ] 测试通过

---

## 📈 性能提升预期

| 指标 | 改进前 | 改进后 | 提升 |
|------|--------|--------|------|
| 平均响应时间 | ~500ms | ~200ms | 60% ⬇️ |
| 缓存命中 | 0% | 60%+ | 60% ⬆️ |
| 可观测性 | 无 | 完整日志 | ✅ |
| 错误追踪 | 基础 | 结构化 | ✅ |

---

## 🚀 下一步（Phase 2）

完成 Phase 1 后，继续：

1. **监控和恢复**（1-2 天）
   - Prometheus 指标
   - 错误追踪（Sentry）
   - 重试机制

2. **高级工具**（2-3 天）
   - 地址验证
   - 地理编码

3. **安全防护**（1 天）
   - API Key 认证
   - 速率限制

需要我提供 Phase 2 的实现代码吗？
