# Backend Scripts

Utility and pipeline scripts for the ChikGuard backend. These are **not part of the main application** — they are standalone tools for data processing, model management, and development tasks.

## Scripts

| Script | Description |
|---|---|
| `data_augmentation.py` | Augments training datasets for YOLO fine-tuning |
| `frame_extractor.py` | Extracts frames from video files for dataset labeling |
| `video_processor.py` | Batch video processing utilities |
| `vision_pipeline.py` | Standalone vision pipeline runner (for testing) |
| `vision_pipeline_sota.py` | Experimental SOTA vision pipeline |
| `yolo_tracker.py` | Standalone YOLO tracking script for testing |
| `supabase_sync_worker.py` | Manual Supabase sync worker trigger |
| `scratch_purge.py` | Cleans up the backend scratch directory |
| `cv_upgrade.py` | OpenCV upgrade/check utility |
| `model_export_pipeline.sh` | Exports YOLO models to ONNX format |
| `test_fsm.py` | Unit test runner for the FSM state machine |
| `refactor_login.py` | One-time login page refactoring script (dev) |
| `refactor_views.py` | One-time views refactoring script (dev) |

## Usage

Run any script from the project root:

```bash
PYTHONPATH=backend python backend/scripts/<script_name>.py
```
