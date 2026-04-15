import math

class Tracker:
    """
    Tracker básico baseado em distância (Centroid Tracking)
    Pode ser expandido para ByteTrack ou BoT-SORT posteriormente.
    """
    def __init__(self, max_disappeared=50, max_distance=50):
        self.next_object_id = 0
        self.objects = {} # id -> centroid (x,y)
        self.disappeared = {} # id -> count
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid):
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]

    def update(self, rects):
        """
        Atualiza o tracker com as novas detecções (rects: list of (x1, y1, x2, y2))
        """
        if len(rects) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        input_centroids = []
        for (x1, y1, x2, y2) in rects:
            cx = int((x1 + x2) / 2.0)
            cy = int((y1 + y2) / 2.0)
            input_centroids.append((cx, cy))

        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(input_centroids[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # Simplistic nearest-neighbor logic
            used_rows = set()
            used_cols = set()

            for i, object_centroid in enumerate(object_centroids):
                best_dist = float('inf')
                best_col = -1
                for j, input_centroid in enumerate(input_centroids):
                    if j in used_cols:
                        continue
                    dist = math.hypot(object_centroid[0] - input_centroid[0],
                                      object_centroid[1] - input_centroid[1])
                    if dist < best_dist and dist < self.max_distance:
                        best_dist = dist
                        best_col = j

                if best_col != -1:
                    object_id = object_ids[i]
                    self.objects[object_id] = input_centroids[best_col]
                    self.disappeared[object_id] = 0
                    used_rows.add(i)
                    used_cols.add(best_col)

            # Handle disappeared
            for i, object_id in enumerate(object_ids):
                if i not in used_rows:
                    self.disappeared[object_id] += 1
                    if self.disappeared[object_id] > self.max_disappeared:
                        self.deregister(object_id)

            # Register new
            for j in range(len(input_centroids)):
                if j not in used_cols:
                    self.register(input_centroids[j])

        return self.objects
