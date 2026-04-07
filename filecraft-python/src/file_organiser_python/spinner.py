import itertools
import sys
import threading
import time
from contextlib import contextmanager
from typing import Generator, Optional, TextIO


def _is_tty(stream: TextIO) -> bool:
    try:
        return stream.isatty()
    except Exception:
        return False


@contextmanager
def cli_spinner(
    message: str,
    *,
    stream: Optional[TextIO] = None,
    interval: float = 0.1,
) -> Generator[None, None, None]:
    target_stream = stream or sys.stderr

    if not _is_tty(target_stream):
        yield
        return

    stop_event = threading.Event()

    def _spin() -> None:
        for frame in itertools.cycle("|/-\\"):
            if stop_event.is_set():
                break
            target_stream.write(f"\r{message}... {frame}")
            target_stream.flush()
            time.sleep(interval)

    spinner_thread = threading.Thread(target=_spin, daemon=True)
    spinner_thread.start()

    success = True
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        stop_event.set()
        spinner_thread.join(timeout=max(interval * 2, 0.2))
        status = "done" if success else "failed"
        target_stream.write(f"\r{message}... {status}\n")
        target_stream.flush()
