# Sentinance API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "full_name": "John Doe"
}
```

### Login
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## Prices

### Get All Prices
```http
GET /api/prices
```

### Get Single Price
```http
GET /api/prices/{symbol}
```

### Get Price History
```http
GET /api/prices/{symbol}/history?limit=50
```

---

## Alerts

### Create Alert
```http
POST /api/alerts
Authorization: Bearer {token}
Content-Type: application/json

{
  "symbol": "BTCUSDT",
  "alert_type": "price_above",
  "target_value": 100000,
  "message": "BTC hit 100k!"
}
```

### List Alerts
```http
GET /api/alerts
Authorization: Bearer {token}
```

### Delete Alert
```http
DELETE /api/alerts/{alert_id}
Authorization: Bearer {token}
```

---

## AI Chat

### Send Message
```http
POST /api/chat
Content-Type: application/json

{
  "message": "Is Bitcoin showing manipulation signals?",
  "use_agent": true
}
```

**Response:**
```json
{
  "role": "assistant",
  "content": "Based on my analysis...",
  "metadata": {
    "model": "langgraph-multi-agent",
    "confidence": 0.85,
    "plan": ["get_current_price", "analyze_whale"]
  }
}
```

### Get Suggestions
```http
GET /api/chat/suggestions
```

---

## News

### Get Latest News
```http
GET /api/news?limit=20
```

### Get News by Topic
```http
GET /api/news/{topic}?limit=10
```

---

## Market Stats

### Get Market Overview
```http
GET /api/stats
```

**Response:**
```json
{
  "total_market_cap": 1870000000000,
  "btc_dominance": 52.3,
  "fear_greed_index": 62,
  "fear_greed_label": "Greed"
}
```

### Get Top Movers
```http
GET /api/stats/movers?limit=5
```

---

## WebSocket

### Price Stream
```
ws://localhost:8000/ws/prices
```

**Message Format:**
```json
{
  "type": "price_update",
  "prices": [
    {"symbol": "BTCUSDT", "price": 95234.56, ...}
  ],
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## Health

```http
GET /health
GET /health/live
GET /health/ready
GET /metrics
```
