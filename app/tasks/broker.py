import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AsyncIO

from app.config import get_settings

redis_broker = RedisBroker(url=get_settings().redis_url)
redis_broker.add_middleware(AsyncIO())
dramatiq.set_broker(redis_broker)
