import asyncio
from uuid import uuid4
from .models import utc_now


class EventBus:
    def __init__(self, store):
        self.store = store
        self.subscribers: set[asyncio.Queue] = set()

    async def publish(self, event_type, payload):
        envelope = {"type": event_type, "data": payload}
        for queue in tuple(self.subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(envelope)

    async def activity(self, message, agent_id=None, job_id=None, event_type="activity", detail=None):
        event = {"id": str(uuid4()), "type": event_type, "timestamp": utc_now(), "message": message, "agent_id": agent_id, "job_id": job_id, "detail": detail or {}}
        self.store.put("events", event)
        await self.publish("activity", event)
        return event
