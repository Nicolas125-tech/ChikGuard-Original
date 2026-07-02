## 2024-07-02 - Batched push notifications to Expo
**Learning:** Sequential HTTP requests in `anomaly_storage_worker` for push notifications (`requests.post` inside a `for token_obj in tokens:` loop) were creating an N+1 blocking I/O bottleneck, heavily delaying the thread if many tokens existed.
**Action:** Always batch identical payloads into single bulk API requests where the external API supports it. In this case, `requests.post` was changed to send a chunk of 100 payloads at a time according to Expo guidelines.
