from typing import Literal

from pydantic import BaseModel


class WebhookAck(BaseModel):
    status: Literal["ok"] = "ok"
