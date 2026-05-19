import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.config import get_settings

redis_broker = RedisBroker(url=get_settings().redis_url)
dramatiq.set_broker(redis_broker)

