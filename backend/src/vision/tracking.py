import math
import numpy as np

try:
    from ultralytics.trackers.byte_tracker import BYTETracker
    # Dummy args structure for BYTETracker init if needed

    class TrackerArgs:
        def __init__(self):
            self.track_high_thresh = 0.5
            self.track_low_thresh = 0.1
            self.new_track_thresh = 0.6
            self.track_buffer = 30
            self.match_thresh = 0.8
    ULTRALYTICS_TRACKER_AVAILABLE = True
except ImportError:
    ULTRALYTICS_TRACKER_AVAILABLE = False
    print("Aviso: 'ultralytics.trackers' não disponível. Fallback para Centroid Tracker modificado.")


class Tracker:
    """
    Agile Tracker baseado no ByteTrack (se disponível) ou Centroid Tracker avançado.
    Lida com pequenas oclusões temporárias mantendo o ID consistente.
    """

    def __init__(self, max_disappeared=50, max_distance=50, use_bytetrack=True):
        self.use_bytetrack = use_bytetrack and ULTRALYTICS_TRACKER_AVAILABLE

        if self.use_bytetrack:
            print("Iniciando BYTETracker para rastreamento ágil...")
            args = TrackerArgs()
            # Frame rate is arbitrary for initialization, track_buffer handles disappearance
            self.tracker = BYTETracker(args, frame_rate=30)
        else:
            print("Iniciando Custom Centroid Tracker (Fallback)...")
            self.next_object_id = 0
            self.objects = {}  # id -> centroid (x,y)
            self.disappeared = {}  # id -> count
            self.max_disappeared = max_disappeared
            self.max_distance = max_distance

    def _register(self, centroid):
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1

    def _deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]

    def update(self, detections, img_info=None):
        """
        Atualiza o tracker.
        :param detections: list of dicts from vision_engine predict [{'bbox':[x1,y1,x2,y2], 'score':conf, ...}, ...]
        :param img_info: tuple (height, width) of the image, required for BYTETracker
        :return: dict of object_id -> {'bbox': [x1,y1,x2,y2], 'centroid': (cx,cy)}
        """
        tracked_objects = {}

        if self.use_bytetrack:
            if not detections:
                return tracked_objects

            if img_info is None:
                img_info = (1080, 1920)  # Dummy fallback if not provided

            # Convert detections to format expected by BYTETracker:
            # numpy array of [x1, y1, x2, y2, score, class_id]
            det_array = []
            for d in detections:
                box = d['bbox']
                det_array.append([box[0], box[1], box[2], box[3], d.get('score', 1.0), d.get('category_id', 0)])

            det_array = np.array(det_array)

            # Update BYTETracker
            # img_info and img_size are required, passing same for both
            tracks = self.tracker.update(det_array, img_info, img_info)

            for track in tracks:
                if not track.is_activated:
                    continue
                # tlbr: top left bottom right
                bbox = track.tlbr
                track_id = track.track_id

                cx = int((bbox[0] + bbox[2]) / 2.0)
                cy = int((bbox[1] + bbox[3]) / 2.0)

                tracked_objects[track_id] = {
                    'bbox': [int(x) for x in bbox],
                    'centroid': (cx, cy)
                }

            return tracked_objects

        else:
            # Fallback Centroid Tracker logic
            rects = [d['bbox'] for d in detections]

            if len(rects) == 0:
                for object_id in list(self.disappeared.keys()):
                    self.disappeared[object_id] += 1
                    if self.disappeared[object_id] > self.max_disappeared:
                        self._deregister(object_id)
                # Return current known objects just to keep API consistent, or empty
                return {k: {'bbox': None, 'centroid': v} for k, v in self.objects.items()}

            input_centroids = []
            for (x1, y1, x2, y2) in rects:
                cx = int((x1 + x2) / 2.0)
                cy = int((y1 + y2) / 2.0)
                input_centroids.append((cx, cy))

            if len(self.objects) == 0:
                for i in range(len(input_centroids)):
                    self._register(input_centroids[i])
            else:
                object_ids = list(self.objects.keys())
                object_centroids = list(self.objects.values())

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
                            self._deregister(object_id)

                # Register new
                for j in range(len(input_centroids)):
                    if j not in used_cols:
                        self._register(input_centroids[j])

            # Build result
            for obj_id, centroid in self.objects.items():
                # We don't have the updated bbox for disappeared objects easily accessible in this simple fallback
                # For new/updated ones, we could match, but we just return centroid
                tracked_objects[obj_id] = {'bbox': None, 'centroid': centroid}

            return tracked_objects
