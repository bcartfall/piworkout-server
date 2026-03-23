import threading
import logging
import os

logger = logging.getLogger('piworkout-server')

DEBUG_LOCKS=str(os.getenv('DEBUG_LOCKS', 'False')).lower() == 'true'

class LoggingLock:
    def __init__(self, name="Lock"):
        self._lock = threading.Lock()
        self.name = name

    def acquire(self, blocking=True, timeout=-1, stackLevel=2):
        if DEBUG_LOCKS:
            logger.debug(f"[Lock] Attempting to acquire {self.name}...", stacklevel=stackLevel)
        result = self._lock.acquire(blocking, timeout)
        if DEBUG_LOCKS:
            if result:
                logger.debug(f"[Lock] Acquired {self.name}", stacklevel=stackLevel)
            else:
                logger.debug(f"[Lock] Failed to acquire {self.name}", stacklevel=stackLevel)
        return result

    def release(self, stackLevel=2):
        if DEBUG_LOCKS:
            logger.debug(f"[Lock] Releasing {self.name}...", stacklevel=stackLevel)
        self._lock.release()
        if DEBUG_LOCKS:
            logger.debug(f"[Lock] Released {self.name}", stacklevel=stackLevel)

    # These allow the lock to work with the 'with' statement
    def __enter__(self):
        self.acquire(stackLevel=3)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release(stackLevel=3)