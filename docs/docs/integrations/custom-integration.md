---
sidebar_position: 3
---

# Custom Integration

Build custom integrations with Vidurai for your specific use case.

## Basic Integration Pattern

```python
from vidurai import Vidurai
from typing import List, Dict, Any

class MyCustomSystem:
    def __init__(self):
        self.memory = Vidurai(
            compression_threshold=0.8,
            enable_decay=True
        )

    def process(self, input_data: str) -> str:
        # 1. Recall relevant context
        context = self._get_context(input_data)

        # 2. Process with your custom logic
        result = self._do_processing(input_data, context)

        # 3. Store the result
        self._store_result(input_data, result)

        return result

    def _get_context(self, query: str) -> List[Dict]:
        return self.memory.recall(query, limit=5)

    def _do_processing(self, input_data: str, context: List[Dict]) -> str:
        # Your custom logic here
        pass

    def _store_result(self, input_data: str, result: str):
        self.memory.store(
            f"Input: {input_data}\nOutput: {result}",
            importance=0.7
        )
```

## Integration with Web Frameworks

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from vidurai import Vidurai
from pydantic import BaseModel

app = FastAPI()
memory = Vidurai()

class Query(BaseModel):
    text: str
    importance: float = 0.7

class RecallQuery(BaseModel):
    query: str
    limit: int = 5
    min_importance: float = 0.0

@app.post("/store")
async def store_memory(query: Query):
    memory.store(query.text, importance=query.importance)
    return {"status": "stored", "text": query.text}

@app.post("/recall")
async def recall_memory(query: RecallQuery):
    results = memory.recall(
        query.query,
        limit=query.limit,
        min_importance=query.min_importance
    )
    return {"results": results}

@app.get("/stats")
async def get_stats():
    return memory.get_memory_stats()

@app.delete("/clear")
async def clear_memory(threshold: float = 0.3):
    memory.clear_below_threshold(threshold)
    return {"status": "cleared"}
```

### Flask Integration

```python
from flask import Flask, request, jsonify
from vidurai import Vidurai

app = Flask(__name__)
memory = Vidurai()

@app.route('/store', methods=['POST'])
def store():
    data = request.json
    memory.store(data['text'], importance=data.get('importance', 0.7))
    return jsonify({'status': 'stored'})

@app.route('/recall', methods=['POST'])
def recall():
    data = request.json
    results = memory.recall(
        data['query'],
        limit=data.get('limit', 5)
    )
    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(debug=True)
```

## Integration with Databases

### PostgreSQL + Vidurai

```python
import psycopg2
from vidurai import Vidurai
from datetime import datetime

class DatabaseMemorySystem:
    def __init__(self, db_config: dict):
        self.conn = psycopg2.connect(**db_config)
        self.memory = Vidurai()

    def store_with_db(self, user_id: int, content: str, importance: float = 0.7):
        # Store in database
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO memories (user_id, content, created_at) VALUES (%s, %s, %s)",
            (user_id, content, datetime.now())
        )
        self.conn.commit()

        # Store in Vidurai
        self.memory.store(
            f"User {user_id}: {content}",
            importance=importance
        )

    def recall_with_db(self, user_id: int, query: str, limit: int = 5):
        # Recall from Vidurai first (fast)
        memory_results = self.memory.recall(
            f"User {user_id} {query}",
            limit=limit
        )

        # Fallback to database if needed
        if not memory_results:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT content FROM memories WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                (user_id, limit)
            )
            db_results = cursor.fetchall()
            return [{'content': r[0], 'source': 'database'} for r in db_results]

        return memory_results
```

## Integration with Message Queues

### RabbitMQ + Vidurai

```python
import pika
import json
from vidurai import Vidurai

class MessageQueueMemory:
    def __init__(self, rabbitmq_url: str):
        self.connection = pika.BlockingConnection(
            pika.URLParameters(rabbitmq_url)
        )
        self.channel = self.connection.channel()
        self.memory = Vidurai()

        # Declare queue
        self.channel.queue_declare(queue='memory_queue')

    def consume_and_store(self):
        def callback(ch, method, properties, body):
            data = json.loads(body)

            # Store in Vidurai
            self.memory.store(
                data['content'],
                importance=data.get('importance', 0.7)
            )

            # Process based on memory context
            context = self.memory.recall(data['content'], limit=3)
            result = self._process_with_context(data, context)

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(
            queue='memory_queue',
            on_message_callback=callback
        )

        print('Starting to consume messages...')
        self.channel.start_consuming()

    def _process_with_context(self, data, context):
        # Your processing logic here
        pass
```

## Custom Memory Backend

```python
from vidurai import Vidurai
from typing import List, Dict
import redis

class RedisBackedVidurai(Vidurai):
    def __init__(self, redis_url: str, **kwargs):
        super().__init__(**kwargs)
        self.redis_client = redis.from_url(redis_url)

    def store(self, content: str, importance: float = 0.7):
        # Store in Vidurai
        memory_id = super().store(content, importance)

        # Also store in Redis for persistence
        self.redis_client.hset(
            f"memory:{memory_id}",
            mapping={
                'content': content,
                'importance': importance,
                'timestamp': datetime.now().isoformat()
            }
        )

        return memory_id

    def recall(self, query: str, limit: int = 5, **kwargs) -> List[Dict]:
        # Try Vidurai first
        results = super().recall(query, limit, **kwargs)

        # Fallback to Redis if needed
        if not results:
            keys = self.redis_client.keys("memory:*")
            results = []
            for key in keys[:limit]:
                data = self.redis_client.hgetall(key)
                if query.lower() in data.get('content', '').lower():
                    results.append(data)

        return results
```

## Middleware Pattern

```python
from typing import Callable
from vidurai import Vidurai

class MemoryMiddleware:
    def __init__(self, memory: Vidurai):
        self.memory = memory

    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Pre-processing: Get context
            if args:
                context = self.memory.recall(str(args[0]), limit=3)
                kwargs['context'] = context

            # Execute function
            result = func(*args, **kwargs)

            # Post-processing: Store result
            self.memory.store(
                f"Function: {func.__name__}\nInput: {args}\nOutput: {result}",
                importance=0.6
            )

            return result

        return wrapper

# Usage
memory = Vidurai()
middleware = MemoryMiddleware(memory)

@middleware
def process_data(data: str, context: list = None) -> str:
    if context:
        print(f"Using context: {context}")
    return f"Processed: {data}"

result = process_data("user input")
```

## Best Practices

1. **Separate concerns**
   - Use Vidurai for semantic memory
   - Use databases for structured data
   - Use caching for frequently accessed data

2. **Error handling**
   ```python
   try:
       memory.store(data)
   except Exception as e:
       logger.error(f"Failed to store memory: {e}")
       # Fallback to database or queue
   ```

3. **Monitoring**
   ```python
   import logging

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   stats = memory.get_memory_stats()
   logger.info(f"Memory stats: {stats}")
   ```

4. **Testing**
   ```python
   import pytest
   from vidurai import Vidurai

   @pytest.fixture
   def memory():
       return Vidurai(enable_decay=False)  # Disable for deterministic tests

   def test_store_recall(memory):
       memory.store("test data", importance=0.7)
       results = memory.recall("test")
       assert len(results) > 0
   ```

See [LangChain](./langchain.md) and [LlamaIndex](./llamaindex.md) integrations for framework-specific examples.
