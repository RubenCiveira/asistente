from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass


class WorkLockError(RuntimeError):
    pass


@dataclass
class WorkLock:
    lock_path: str
    created: bool = False

    def acquire(self) -> None:
        os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)

        # O_EXCL => falla si ya existe
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            # lock ya existe
            raise WorkLockError(f"Lock activo: {self.lock_path}")

        try:
            payload = {
                "pid": os.getpid(),
                "ts": time.time(),
            }
            os.write(fd, json.dumps(payload).encode("utf-8"))
            self.created = True
        finally:
            os.close(fd)

    def release(self) -> None:
        if self.created and os.path.exists(self.lock_path):
            try:
                os.remove(self.lock_path)
            except OSError:
                pass

    def __enter__(self) -> "WorkLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
