from typing import Annotated

from pydantic import BaseModel, ConfigDict, StrictBool, StringConstraints


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    completed: StrictBool


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    completed: bool
