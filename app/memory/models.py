from datetime import datetime
from pydantic import BaseModel


class MemoryFact(BaseModel):
    id: str
    user_id: str
    text: str
    source: str
    created_at: datetime