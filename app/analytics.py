from amplitude import Amplitude, BaseEvent
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, api_key: str):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.client = Amplitude(api_key)

    def track_event(self, user_id: int, event_type: str, event_props: dict = None):
        try:
            self.executor.submit(
                self.client.track(
                    BaseEvent(
                        user_id=str(user_id),
                        event_type=event_type,
                        event_properties=event_props)
                )
            )
        except Exception as e:
            logger.error(f"Amplitude error: {e}")
