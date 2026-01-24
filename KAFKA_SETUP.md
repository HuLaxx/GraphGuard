# Kafka Setup Instructions

## Current Status
Docker is installed but **Docker Desktop is not running**.

## Option 1: Start Docker Desktop (Recommended for Full Kafka)

### Windows
1. **Press Windows key** and search for "Docker Desktop"
2. **Click** to start Docker Desktop
3. **Wait** for the whale icon to appear in system tray (30-60 seconds)
4. **Verify** Docker is running:
   ```bash
   docker ps
   ```
5. **Then run:**
   ```bash
   docker-compose up -d zookeeper kafka schema-registry
   ```

### What You'll Get
- ✅ Full Kafka cluster
- ✅ Zookeeper for coordination
- ✅ Schema Registry for Avro
- ✅ Production-grade event streaming

**Time: ~2 minutes**

---

## Option 2: Lightweight Alternative (No Docker Required)

I've created a **Redis Streams-based** event pipeline that works without Kafka:

### Files Created
- `streaming_producer.py` - Publishes transactions to Redis
- `streaming_consumer.py` - Processes transactions from Redis
- `test_streaming.py` - Demo script

### How to Use
```bash
# Start the consumer (in one terminal)
python streaming_consumer.py

# Run the producer (in another terminal)
python streaming_producer.py

# Or run the test demo
python test_streaming.py
```

### What It Does
- ✅ Real-time transaction streaming
- ✅ Event persistence
- ✅ Consumer groups
- ✅ Works with existing Redis

**Time: < 30 seconds**

---

## Comparison

| Feature | Kafka (Docker) | Redis Streams |
|---------|----------------|---------------|
| Setup Time | 2-3 min | 30 sec |
| Requirements | Docker Desktop | Redis (running) |
| Scalability | Excellent | Good |
| Perfect For | Production | Demo/POC |

---

## Recommendation

**For Demo/Testing:** Use Option 2 (Redis Streams)  
**For Production:** Use Option 1 (Full Kafka)

Choose based on your immediate needs!
