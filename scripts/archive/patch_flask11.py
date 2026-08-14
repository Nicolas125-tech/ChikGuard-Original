# Ah! Look at lines 153-155:
# future = asyncio.run_coroutine_threadsafe(
#     _process_offer(params["sdp"], params["type"], pc_id, get_global_frame), webrtc_loop
# )
#
# webrtc_loop is defined somewhere else in the file?
# Let's check where webrtc_loop is defined.
