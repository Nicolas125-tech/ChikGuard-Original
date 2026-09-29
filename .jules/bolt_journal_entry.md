## 2024-05-18 - Graceful Thread Shutdown in Background Workers
**Learning:** Python's `time.sleep()` in background threads (like the continuous audio processing worker) prevents the thread from being instantly responsive to stop/shutdown signals, which delays application teardown and tests.
**Action:** Replace `time.sleep(timeout)` loops in background threads with a `threading.Event` and `self._stop_event.wait(timeout)` to allow immediate interruption for a graceful and responsive shutdown.
