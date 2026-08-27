from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MaterialStatus


class MaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    file_size: int
    status: MaterialStatus
    title: str
    processing_error: str | None = None
    created_at: datetime
    updated_at: datetime
