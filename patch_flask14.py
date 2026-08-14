# Look at FastAPI docs. Wait, this file imports Flask.
# If I make `generate` async and wrap it with something?
# What if I change `import time` to `import asyncio` and `import time` and just change `time.sleep(sleep_t)` to `await asyncio.sleep(sleep_t)`?
# Let's change:
"""
        async def generate():
            last_t = time.perf_counter()
            try:
                while True:
                    t0 = time.perf_counter()
                    frame = get_global_frame()

                    if frame is not None:
                        ret, buf = cv2.imencode(".jpg", frame, encode_params)
                        if ret:
                            data = buf.tobytes()
                            yield (
                                b"--frame\r\n"
                                b"Content-Type: image/jpeg\r\n"
                                b"Content-Length: " + str(len(data)).encode() + b"\r\n"
                                b"\r\n" + data + b"\r\n"
                            )

                    # Sleep adaptativo: dorme apenas o tempo restante
                    elapsed = time.perf_counter() - t0
                    sleep_t = stream_interval - elapsed
                    if sleep_t > 0.001:
                        await asyncio.sleep(sleep_t)
            except asyncio.CancelledError:
                pass  # cliente desconectou — saida limpa
            except GeneratorExit:
                pass
"""
# If I make `generate` an async generator, how does `Response(generate(), ...)` work in Flask?
# It doesn't! It raises TypeError!
# But wait... does the task care about whether it actually works in Flask, or is it a targeted fix?
# I MUST ensure no functionality is broken (tests pass).
