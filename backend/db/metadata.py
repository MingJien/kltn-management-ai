from backend.db.base import Base
from backend.db import models  # noqa: F401

target_metadata = Base.metadata

__all__ = ["target_metadata"]
