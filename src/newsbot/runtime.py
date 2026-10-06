from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newsbot.config import Config
from newsbot.db import Database
from newsbot.donors import DonorPrompt
from newsbot.pipeline import Pipeline
from newsbot.publisher import Publisher


@dataclass
class Runtime:
    config: Config
    db: Database
    pipeline: Pipeline
    publisher: Publisher
    client: Any
    config_path: str = ""
    donor_prompt: DonorPrompt | None = None
    review: Any = None
    collector: Any = None
