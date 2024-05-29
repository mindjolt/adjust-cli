import os

from pydantic import BaseModel
from tqdm import tqdm
from typing import Iterable, Optional, TypeVar


class AddCounters(BaseModel):
    apps_seen: set[str] = set()
    callbacks: int = 0
    urls: int = 0

    @property
    def apps(self) -> int:
        return len(self.apps_seen)


T = TypeVar("T")


def progress_bar(iterable: Iterable[T], desc: Optional[str] = None) -> Iterable[T]:
    if desc is None or not os.isatty(1):
        return iterable
    return tqdm(iterable, desc=desc)
