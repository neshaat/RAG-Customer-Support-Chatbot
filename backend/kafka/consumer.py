"""
Background Kafka consumer — run separately for event logging/monitoring.
Usage:  python -m backend.kafka.consumer
"""
import json
import threading
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from loguru import logger
from backend.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC_QUERIES,
    KAFKA_TOPIC_RESPONSES,
    KAFKA_TOPIC_EVALS,
)


def _consume(topics: list[str]):
    try:
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=1000,
        )
        logger.info(f"Consumer listening on: {topics}")
        for msg in consumer:
            logger.info(f"[{msg.topic}] {msg.value}")
    except NoBrokersAvailable:
        logger.warning("Consumer: Kafka unavailable, skipping.")
    except Exception as e:
        logger.error(f"Consumer error: {e}")


def start_background_consumer():
    """Start consumer in a daemon thread (called from app.py)."""
    topics = [KAFKA_TOPIC_QUERIES, KAFKA_TOPIC_RESPONSES, KAFKA_TOPIC_EVALS]
    t = threading.Thread(target=_consume, args=(topics,), daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    topics = [KAFKA_TOPIC_QUERIES, KAFKA_TOPIC_RESPONSES, KAFKA_TOPIC_EVALS]
    _consume(topics)
