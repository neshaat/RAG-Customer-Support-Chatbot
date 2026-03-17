import json
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from loguru import logger
from backend.config import KAFKA_BOOTSTRAP_SERVERS


_producer = None


def get_producer() -> KafkaProducer | None:
    """Lazy-init Kafka producer; returns None if Kafka is unavailable (graceful degradation)."""
    global _producer
    if _producer is not None:
        return _producer
    try:
        _producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=3,
            request_timeout_ms=5000,
        )
        logger.info("Kafka producer connected.")
    except NoBrokersAvailable:
        logger.warning("Kafka unavailable — events will not be streamed.")
        _producer = None
    return _producer


def publish_event(topic: str, event: dict) -> bool:
    """
    Publish a JSON event to a Kafka topic.
    Returns True on success, False if Kafka is unavailable.
    """
    producer = get_producer()
    if producer is None:
        return False
    try:
        future = producer.send(topic, value=event)
        future.get(timeout=5)
        logger.debug(f"Published to {topic}: {list(event.keys())}")
        return True
    except Exception as e:
        logger.error(f"Kafka publish error: {e}")
        return False
