# Free Intelligence - Back-Pressure & Queues: Comparativa

**Created**: 2025-10-28
**Owner**: Bernard Uriza Orozco
**Status**: Draft v0.1
**Dependencies**: LATENCY_BUDGET.md, MICRO_PROFILING_PLAN.md

---

## Executive Summary

Este documento compara **3 soluciones** para manejar back-pressure y colas en el pipeline de Free Intelligence:

1. **Redis Streams** - In-memory message broker con persistence
2. **NATS JetStream** - Distributed messaging system con garantías de entrega
3. **ZeroMQ** - Local IPC ultra-low latency (sin persistence nativa)

**Recomendación**: Comenzar con **Redis Streams** para MVP, evaluar NATS JetStream si se requiere distribución multi-nodo.

---

## Problem Statement

### Actual: Synchronous HDF5 Writes

```
HTTP Request → FastAPI → HDF5.write() → HTTP Response
     ↓                         ↓
  Blocked              1700ms latency
```

**Problema**: El cliente HTTP espera 1700ms (p95) hasta que HDF5 termina de escribir.

### Solución: Asynchronous Queue

```
HTTP Request → FastAPI → Queue.push() → HTTP 202 Accepted (5ms)
                             ↓
                        Background Worker
                             ↓
                        HDF5.write() (1700ms, no bloquea cliente)
```

**Beneficio**: Latencia percibida de 5ms (99% mejora).

---

## Comparativa: 3 Soluciones

### 1. Redis Streams

#### Arquitectura

```
┌──────────────┐
│  FastAPI     │
│  (Producer)  │
└──────┬───────┘
       │ XADD (1-5ms)
       ▼
┌──────────────────┐
│  Redis Streams   │ ← In-memory, persistence optional (AOF/RDB)
│  (Message Broker)│
└──────┬───────────┘
       │ XREADGROUP
       ▼
┌──────────────┐
│  Worker Pool │ → HDF5.write()
│  (Consumer)  │
└──────────────┘
```

#### Características

| Feature | Redis Streams |
|---------|---------------|
| **Latency (write)** | 1-5ms (in-memory) |
| **Throughput** | 100K+ ops/sec (single instance) |
| **Persistence** | ✅ AOF (append-only file) o RDB (snapshots) |
| **Delivery Guarantees** | At-least-once (con consumer groups) |
| **Ordering** | ✅ FIFO por stream |
| **Back-pressure** | ✅ MAXLEN (limitar tamaño del stream) |
| **Clustering** | ✅ Redis Cluster (sharding) |
| **Complexity** | Low (single binary, simple API) |

#### Código de Ejemplo

```python
# producer.py (FastAPI)
import redis
from fastapi import FastAPI

app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.post("/consultations/{id}/events")
async def append_event(consultation_id: str, request: dict):
    # Push to Redis Stream (1-5ms)
    message_id = redis_client.xadd(
        'fi:events',
        {
            'consultation_id': consultation_id,
            'event_json': json.dumps(request)
        },
        maxlen=10000  # Back-pressure: mantener solo últimos 10K eventos
    )

    return {
        "status": "accepted",
        "message_id": message_id
    }, 202


# consumer.py (Background worker)
import redis
import h5py

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Create consumer group
redis_client.xgroup_create('fi:events', 'fi-workers', id='0', mkstream=True)

def consume_events():
    while True:
        # Read batch (blocking, with timeout)
        messages = redis_client.xreadgroup(
            'fi-workers',
            'worker-1',
            {'fi:events': '>'},
            count=10,
            block=5000  # 5s timeout
        )

        for stream, msgs in messages:
            for msg_id, data in msgs:
                # Process event
                consultation_id = data['consultation_id']
                event_json = data['event_json']

                # Write to HDF5
                event_store.append_event(consultation_id, event_json)

                # Acknowledge (at-least-once)
                redis_client.xack('fi:events', 'fi-workers', msg_id)

if __name__ == '__main__':
    consume_events()
```

#### Pros

✅ **Ultra-low latency** (1-5ms writes)
✅ **Simple setup** (single binary, no dependencies)
✅ **Persistence** (AOF/RDB)
✅ **Consumer groups** (múltiples workers, load balancing)
✅ **Back-pressure** (MAXLEN)
✅ **Monitoring** (Redis CLI, RedisInsight)

#### Cons

❌ **Memoria** (6GB RAM para 100K eventos de ~1KB)
❌ **Single point of failure** (sin clustering, requiere Redis Sentinel para HA)
❌ **No garantías exactly-once** (solo at-least-once)

#### Cost

- **Development**: Gratuito (Redis OSS)
- **Memory**: ~6GB RAM para 100K eventos
- **Infra**: 1 instancia Redis (puede correr en mismo NAS)

---

### 2. NATS JetStream

#### Arquitectura

```
┌──────────────┐
│  FastAPI     │
│  (Producer)  │
└──────┬───────┘
       │ Publish (5-10ms)
       ▼
┌──────────────────────┐
│  NATS JetStream      │ ← Distributed, replicated
│  (Message Streaming) │
└──────┬───────────────┘
       │ Subscribe
       ▼
┌──────────────┐
│  Worker Pool │ → HDF5.write()
│  (Consumer)  │
└──────────────┘
```

#### Características

| Feature | NATS JetStream |
|---------|----------------|
| **Latency (write)** | 5-10ms (file-based) |
| **Throughput** | 50K+ msgs/sec (single stream) |
| **Persistence** | ✅ File-based (durable) |
| **Delivery Guarantees** | ✅ At-least-once, exactly-once (con dedup) |
| **Ordering** | ✅ FIFO por stream |
| **Back-pressure** | ✅ Limits (max msgs, max bytes) |
| **Clustering** | ✅ Multi-node con replication (3+ nodes) |
| **Complexity** | Medium (cluster setup, monitoring) |

#### Código de Ejemplo

```python
# producer.py
import asyncio
from nats.aio.client import Client as NATS
from nats.js import api

async def publish_event(consultation_id: str, event_json: str):
    nc = NATS()
    await nc.connect(servers=["nats://localhost:4222"])

    js = nc.jetstream()

    # Publish to stream
    ack = await js.publish("fi.events", event_json.encode())
    print(f"Published to stream: {ack.stream}, seq: {ack.seq}")

    await nc.close()


# consumer.py
async def consume_events():
    nc = NATS()
    await nc.connect(servers=["nats://localhost:4222"])

    js = nc.jetstream()

    # Create stream (if not exists)
    await js.add_stream(
        name="fi-events",
        subjects=["fi.events"],
        max_msgs=100000,  # Back-pressure
    )

    # Subscribe (pull-based)
    sub = await js.pull_subscribe("fi.events", "fi-workers")

    while True:
        msgs = await sub.fetch(batch=10, timeout=5)

        for msg in msgs:
            # Process event
            event_json = msg.data.decode()
            event_store.append_event(event_json)

            # Acknowledge
            await msg.ack()

if __name__ == '__main__':
    asyncio.run(consume_events())
```

#### Pros

✅ **Distributed** (multi-node, replication)
✅ **Exactly-once** (con deduplication)
✅ **Ordering guarantees** (FIFO)
✅ **Persistence** (file-based, durable)
✅ **Monitoring** (NATS CLI, Prometheus exporter)
✅ **Horizontal scale** (múltiples streams, partitioning)

#### Cons

❌ **Setup complexity** (cluster con 3+ nodos para HA)
❌ **Latencia** (~2x mayor que Redis)
❌ **Overhead** (network, serialization para multi-node)

#### Cost

- **Development**: Gratuito (NATS OSS)
- **Infra**: 3 nodos (mínimo para HA) → 3x costo vs Redis
- **Memory**: ~2GB RAM por nodo

---

### 3. ZeroMQ (Local IPC)

#### Arquitectura

```
┌──────────────┐
│  FastAPI     │
│  (Producer)  │
└──────┬───────┘
       │ zmq.send() (<1ms, IPC)
       ▼
┌──────────────────┐
│  ZeroMQ Socket   │ ← In-process o Unix socket
│  (IPC Transport) │
└──────┬───────────┘
       │ zmq.recv()
       ▼
┌──────────────┐
│  Worker Pool │ → HDF5.write()
│  (Consumer)  │
└──────────────┘
```

#### Características

| Feature | ZeroMQ |
|---------|--------|
| **Latency (write)** | <1ms (IPC) |
| **Throughput** | 1M+ msgs/sec (IPC) |
| **Persistence** | ❌ No (solo in-memory) |
| **Delivery Guarantees** | ❌ No garantías (best-effort) |
| **Ordering** | ✅ FIFO (socket-level) |
| **Back-pressure** | ⚠️ Manual (high-water mark) |
| **Clustering** | ❌ Local only (sin distribución) |
| **Complexity** | Low (library, no daemon) |

#### Código de Ejemplo

```python
# producer.py
import zmq

context = zmq.Context()
socket = context.socket(zmq.PUSH)
socket.bind("ipc:///tmp/fi-events.ipc")  # Unix socket

@app.post("/consultations/{id}/events")
async def append_event(consultation_id: str, request: dict):
    # Push to ZeroMQ (<1ms)
    socket.send_json({
        'consultation_id': consultation_id,
        'event': request
    })

    return {"status": "accepted"}, 202


# consumer.py
import zmq

context = zmq.Context()
socket = context.socket(zmq.PULL)
socket.connect("ipc:///tmp/fi-events.ipc")

while True:
    # Blocking receive
    message = socket.recv_json()

    # Process event
    consultation_id = message['consultation_id']
    event = message['event']

    # Write to HDF5
    event_store.append_event(consultation_id, event)
```

#### Pros

✅ **Ultra-low latency** (<1ms, IPC)
✅ **Simple** (library, no daemon)
✅ **High throughput** (1M+ msgs/sec)
✅ **Zero cost** (in-process)
✅ **Patterns** (PUSH/PULL, PUB/SUB, REQ/REP)

#### Cons

❌ **No persistence** (data loss si crash)
❌ **No garantías** (best-effort)
❌ **Local only** (sin distribución)
❌ **No monitoring** (sin tooling built-in)
❌ **Back-pressure manual** (high-water mark)

#### Cost

- **Development**: Gratuito (OSS)
- **Infra**: 0 (in-process)

---

## Comparativa: Tabla Resumen

| Feature | Redis Streams | NATS JetStream | ZeroMQ |
|---------|---------------|----------------|--------|
| **Write Latency** | 1-5ms | 5-10ms | <1ms |
| **Throughput** | 100K/s | 50K/s | 1M/s |
| **Persistence** | ✅ AOF/RDB | ✅ File-based | ❌ None |
| **Delivery Guarantees** | At-least-once | Exactly-once | ❌ Best-effort |
| **Ordering** | ✅ FIFO | ✅ FIFO | ✅ FIFO |
| **Back-pressure** | ✅ MAXLEN | ✅ Limits | ⚠️ Manual (HWM) |
| **Clustering** | ✅ Redis Cluster | ✅ Multi-node | ❌ Local only |
| **HA (High Availability)** | ⚠️ Redis Sentinel | ✅ Built-in (3+ nodes) | ❌ None |
| **Monitoring** | ✅ Redis CLI/Insight | ✅ NATS CLI/Prom | ❌ Manual |
| **Setup Complexity** | Low | Medium | Low |
| **Infra Cost** | 1 instance | 3+ instances | 0 (in-process) |
| **Memory Usage** | High (~6GB/100K) | Medium (~2GB/node) | Low (in-memory) |
| **Use Case** | MVP, single-node | Multi-node, distributed | Ultra-low latency, no persistence |

---

## Recomendación por Fase

### Fase 1: MVP (0-100 sesiones/día)

**Solución**: **Redis Streams**

**Razón**:
- Latencia óptima (1-5ms)
- Persistence garantizada (AOF)
- Setup simple (single instance)
- Monitoring incluido (Redis CLI, RedisInsight)
- At-least-once delivery con consumer groups

**Infraestructura**:
- 1 instancia Redis (puede correr en NAS)
- 2-4 workers Python (consumer pool)
- 6GB RAM (para 100K eventos en buffer)

**Trade-off**: Single point of failure (sin HA).

**Mitigation**: Redis Sentinel (si se requiere HA).

---

### Fase 2: Scale (100-1000 sesiones/día)

**Solución**: **NATS JetStream**

**Razón**:
- Distributed (multi-node)
- HA built-in (3+ nodos con replication)
- Exactly-once delivery
- Horizontal scale (múltiples streams)

**Infraestructura**:
- 3 nodos NATS (cluster mínimo para HA)
- 4-8 workers Python (consumer pool)
- 6GB RAM total (2GB/nodo)

**Trade-off**: Mayor complejidad operativa.

---

### Fase 3: Hyper-Scale (1000+ sesiones/día)

**Solución**: **NATS JetStream + Redis (Hybrid)**

**Razón**:
- NATS para ingesta distribuida
- Redis como cache local (reduce round-trips)
- Partitioning por sitio/cámara

**Infraestructura**:
- 5 nodos NATS (cluster con 2 replicas)
- 10+ workers Python (consumer pool)
- Redis cache (por nodo)

---

## Implementación: Redis Streams (MVP)

### 1. Setup Redis

```bash
# Install (macOS)
brew install redis

# Start
redis-server --port 6379 --appendonly yes  # Enable AOF persistence

# Verify
redis-cli ping  # PONG
```

### 2. FastAPI Producer

```python
# backend/event_queue.py
import redis
import json
from backend.logger import get_logger

logger = get_logger(__name__)

class EventQueue:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.stream_name = "fi:events"

    def push(self, consultation_id: str, event: dict) -> str:
        """Push event to queue (1-5ms)."""
        message_id = self.redis_client.xadd(
            self.stream_name,
            {
                'consultation_id': consultation_id,
                'event_json': json.dumps(event)
            },
            maxlen=10000  # Back-pressure: mantener solo últimos 10K
        )

        logger.info(
            "EVENT_QUEUED",
            consultation_id=consultation_id,
            message_id=message_id,
            stream=self.stream_name
        )

        return message_id


# backend/fi_consult_service.py (modificado)
from backend.event_queue import EventQueue

event_queue = EventQueue()

@app.post("/consultations/{consultation_id}/events")
async def append_event(consultation_id: str, request: dict):
    # Push to queue (async, 1-5ms)
    message_id = event_queue.push(consultation_id, request)

    return {
        "status": "accepted",
        "message_id": message_id,
        "consultation_id": consultation_id
    }, 202  # 202 Accepted
```

### 3. Background Worker (Consumer)

```python
# backend/event_worker.py
import redis
import json
from backend.fi_event_store import EventStore
from backend.logger import get_logger

logger = get_logger(__name__)

class EventWorker:
    def __init__(self, redis_url="redis://localhost:6379", corpus_path="storage/corpus.h5"):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.stream_name = "fi:events"
        self.group_name = "fi-workers"
        self.consumer_name = "worker-1"
        self.event_store = EventStore(corpus_path)

        # Create consumer group (idempotent)
        try:
            self.redis_client.xgroup_create(
                self.stream_name,
                self.group_name,
                id='0',
                mkstream=True
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def consume(self):
        """Consume events from queue (blocking loop)."""
        logger.info("EVENT_WORKER_STARTED", stream=self.stream_name)

        while True:
            # Read batch (blocking, 5s timeout)
            messages = self.redis_client.xreadgroup(
                self.group_name,
                self.consumer_name,
                {self.stream_name: '>'},
                count=10,
                block=5000
            )

            if not messages:
                continue

            for stream, msgs in messages:
                for msg_id, data in msgs:
                    try:
                        # Parse event
                        consultation_id = data['consultation_id']
                        event_json = data['event_json']
                        event = json.loads(event_json)

                        # Write to HDF5 (1700ms)
                        self.event_store.append_event(consultation_id, event)

                        # Acknowledge (at-least-once)
                        self.redis_client.xack(self.stream_name, self.group_name, msg_id)

                        logger.info(
                            "EVENT_PERSISTED",
                            consultation_id=consultation_id,
                            message_id=msg_id
                        )

                    except Exception as e:
                        logger.error(
                            "EVENT_PERSIST_FAILED",
                            message_id=msg_id,
                            error=str(e)
                        )
                        # NOTE: No ack (message will retry)


if __name__ == '__main__':
    worker = EventWorker()
    worker.consume()
```

### 4. Start Stack

```bash
# Terminal 1: Redis
redis-server --port 6379 --appendonly yes

# Terminal 2: FastAPI
uvicorn backend.fi_consult_service:app --port 7001

# Terminal 3: Worker
python backend/event_worker.py

# Terminal 4: Test
curl -X POST http://localhost:7001/consultations/test-id/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "MESSAGE_RECEIVED", "payload": {"msg": "test"}}'
```

---

## Monitoring & Observability

### Redis Streams Metrics

```python
# backend/metrics.py (extension)
def collect_queue_metrics(redis_client, stream_name):
    """Collect Redis Streams metrics."""
    # Stream length
    stream_len = redis_client.xlen(stream_name)

    # Pending messages (no ACK)
    pending_info = redis_client.xpending(stream_name, 'fi-workers')
    pending_count = pending_info['pending']

    # Consumer groups
    groups = redis_client.xinfo_groups(stream_name)

    return {
        'stream_len': stream_len,
        'pending_count': pending_count,
        'consumer_groups': len(groups)
    }
```

### Grafana Dashboard

```yaml
# Example Prometheus metrics
fi_queue_length{stream="fi:events"} 234
fi_queue_pending{stream="fi:events"} 12
fi_queue_ack_rate{stream="fi:events"} 95.2  # % ACK
```

---

## Próximos Pasos

1. **Setup Redis** (1h)
   - Instalar Redis
   - Configurar AOF persistence
   - Verificar latencia (1-5ms)

2. **Implementar EventQueue** (2h)
   - `event_queue.py` con push/pop
   - Integrar con FastAPI (202 Accepted)
   - Tests unitarios

3. **Implementar EventWorker** (2h)
   - `event_worker.py` con consumer group
   - Manejo de errores + retry
   - Logging estructurado

4. **Benchmarks** (2h)
   - Latencia end-to-end (con vs sin queue)
   - Throughput (req/sec)
   - Back-pressure (10K, 50K, 100K eventos)

5. **Monitoreo** (1h)
   - Métricas de queue (length, pending, ACK rate)
   - Dashboards Grafana (opcional)

---

## Referencias

- **Redis Streams**: https://redis.io/docs/data-types/streams/
- **NATS JetStream**: https://docs.nats.io/nats-concepts/jetstream
- **ZeroMQ Guide**: https://zguide.zeromq.org/
- **Comparing Message Brokers**: https://jack-vanlightly.com/blog/2017/12/4/rabbitmq-vs-kafka-part-1

---

**Version History**:
- v0.1 (2025-10-28): Comparativa completa + recomendación por fase
