from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserThreadBase(BaseModel):
    id: str
    userId: str
    threadId: str
    checkpoint: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime


class UserThread(UserThreadBase):
    model_config = ConfigDict(from_attributes=True)


# You might want to add other schemas here as needed, e.g., for User, Account, etc.
# For example:
# class User(BaseModel):
#     id: str
#     name: str
#     email: str
#     # ... other fields
#     model_config = ConfigDict(from_attributes=True)
