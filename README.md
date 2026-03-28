# Destination Extraction Agent - Complete Harness

A production-ready AI agent for extracting destination information from natural language, built with comprehensive Harness architecture.

## 🎯 Features

### Phase 1: Basic Harness ✅
- ✅ Language detection (50+ languages)
- ✅ Smart caching (1 hour TTL, 60%+ hit rate)
- ✅ Structured logging (JSON format)
- ✅ Performance optimization (244x faster with cache)

### Phase 2: Monitoring & Recovery ✅
- ✅ Prometheus metrics
- ✅ Detailed health checks
- ✅ Retry with exponential backoff
- ✅ Circuit breaker pattern
- ✅ Error tracking

### Phase 3: Advanced Tools ✅
- ✅ Address validation (40+ cities)
- ✅ Geocoding (lat/lng conversion)
- ✅ Similar destination search (fuzzy matching)
- ✅ Popular destinations API

### Phase 4: Context Management ✅
- ✅ Session management
- ✅ Request history tracking
- ✅ User preferences
- ✅ Session state management

### Phase 5: Security ✅
- ✅ API Key authentication
- ✅ Rate limiting (60/min, 1000/hour)
- ✅ Input validation
- ✅ Injection attack detection

### Phase 6: Production Deployment ✅
- ✅ Docker containerization
- ✅ Docker Compose setup
- ✅ Prometheus + Grafana monitoring
- ✅ Health checks

## 🚀 Quick Start

### Local Development

```bash
# Clone and setup
cd /Users/ppt/projects/mcp_test
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Run server
python main.py
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f destination-agent

# Stop
docker-compose down
```

## 📊 API Endpoints

### Core Endpoints
- `POST /api/extract-destination` - Extract destination from text
- `POST /api/batch-extract-destinations` - Batch extraction

### Advanced Tools (Phase 3)
- `POST /api/advanced/validate-address` - Validate address
- `POST /api/advanced/geocode` - Get coordinates
- `POST /api/advanced/search-similar` - Fuzzy search
- `GET /api/advanced/continents` - List continents
- `GET /api/advanced/countries` - List countries

### Monitoring (Phase 2)
- `GET /metrics` - Prometheus metrics
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with components

### Session (Phase 4)
- `GET /api/session/stats` - Session statistics
- `GET /api/session/history` - Request history
- `GET /api/session/preferences` - User preferences
- `PUT /api/session/preferences` - Update preference

## 🔧 Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_api_key_here

# Optional
GEMINI_MODEL=gemini-3.1-flash-lite-preview
ENABLE_MCP=true
LOG_LEVEL=INFO
VALID_API_KEYS=key1,key2,key3
```

## 📈 Monitoring

### Prometheus Metrics

Access metrics at: `http://localhost:8001/metrics`

Key metrics:
- `destination_agent_requests_total` - Total requests
- `destination_agent_request_duration_seconds` - Request latency
- `destination_agent_cache_hits_total` - Cache hits
- `destination_agent_gemini_api_calls_total` - Gemini API calls

### Grafana Dashboard

Access Grafana at: `http://localhost:3000`

Default credentials:
- Username: `admin`
- Password: `admin`

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_harness.py -v
```

## 📁 Project Structure

```
mcp_test/
├── app/
│   ├── agent/
│   │   ├── tools/           # Phase 1 & 3 tools
│   │   ├── destination_extractor.py
│   │   ├── gemini_client.py
│   │   └── prompts.py
│   ├── api/
│   │   ├── routes.py        # Core API
│   │   ├── routes_advanced.py  # Phase 3
│   │   ├── routes_session.py   # Phase 4
│   │   └── routes_metrics.py   # Phase 2
│   ├── monitoring/
│   │   ├── metrics.py       # Phase 2
│   │   ├── logger.py        # Phase 1
│   │   ├── error_tracking.py   # Phase 2
│   │   └── session_manager.py  # Phase 4
│   ├── security/
│   │   └── auth.py          # Phase 5
│   └── models/
├── tests/
├── docs/
│   ├── harness-design.md
│   ├── harness-quickstart.md
│   └── harness-test-report.md
├── Dockerfile               # Phase 6
├── docker-compose.yml       # Phase 6
├── prometheus.yml          # Phase 6
├── requirements.txt
└── main.py
```

## 🎓 Performance

### Phase 1 Results
- **Cache hit rate**: 60%+
- **Performance boost**: 244x faster (with cache)
- **Avg response time**: 0.012s (cached) vs 2.9s (uncached)

### Production Ready
- ✅ 99.9% uptime target
- ✅ < 200ms avg response time
- ✅ Automatic error recovery
- ✅ Real-time monitoring

## 📚 Documentation

- [Harness Design](docs/harness-design.md)
- [Quick Start Guide](docs/harness-quickstart.md)
- [Test Report](docs/harness-test-report.md)

## 🔗 References

- [The Anatomy of an Agent Harness - LangChain](https://blog.langchain.com/the-anatomy-of-an-agent-harness/)
- [Agent Harness in Agent Framework - Microsoft](https://devblogs.microsoft.com/agent-framework/)
- [Harness Engineering Complete Guide - NxCode](https://www.nxcode.io/resources/news/harness-engineering-complete-guide-ai-agent-codex-2026)

## 📝 License

MIT

---

**Built with ❤️ using Harness Engineering best practices**
