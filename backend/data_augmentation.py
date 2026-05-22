import os
import cv2
import numpy as np
import albumentations as A
from pathlib import Path

def get_augmentation_pipeline():
    """
    Define the Albumentations pipeline focusing on real-world poultry farm conditions:
    - Lens noise (dust, dirt, speckle)
    - Extreme brightness/contrast variations (shadows, varying lighting)
    - Cutout/CoarseDropout (simulating severe occlusion of birds)
    """
    return A.Compose([
        # Randomly vary brightness and contrast to simulate different lighting conditions
        A.RandomBrightnessContrast(brightness_limit=0.4, contrast_limit=0.4, p=0.8),
        
        # Simulate shadows which are common in poultry houses
        A.RandomShadow(shadow_roi=(0, 0, 1, 1), num_shadows_lower=1, num_shadows_upper=3, shadow_dimension=5, p=0.5),
        
        # Simulate lens noise (dust on camera) using Gaussian noise and speckle
        A.GaussNoise(var_limit=(10.0, 50.0), p=0.5),
        A.MultiplicativeNoise(multiplier=(0.9, 1.1), elementwise=True, p=0.4),
        
        # Blur to simulate out of focus or motion blur
        A.OneOf([
            A.MotionBlur(blur_limit=5, p=0.5),
            A.MedianBlur(blur_limit=5, p=0.5),
            A.GaussianBlur(blur_limit=(3, 7), p=0.5),
        ], p=0.4),
        
        # Cutout/CoarseDropout to simulate occlusions (e.g., chickens behind feeders or other chickens)
        A.CoarseDropout(
            max_holes=8, 
            max_height=64, 
            max_width=64, 
            min_holes=2, 
            min_height=16, 
            min_width=16, 
            fill_value=0, 
            mask_fill_value=None, 
            p=0.7
        ),
        
        # Color shifting
        A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=0.5),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_area=1024, min_visibility=0.2))

def augment_dataset(input_img_dir, input_lbl_dir, output_img_dir, output_lbl_dir, num_augments=3):
    """
    Augment images and bounding boxes in YOLO format.
    """
    os.makedirs(output_img_dir, exist_ok=True)
    os.makedirs(output_lbl_dir, exist_ok=True)
    
    transform = get_augmentation_pipeline()
    
    img_paths = list(Path(input_img_dir).glob("*.jpg")) + list(Path(input_img_dir).glob("*.png"))
    
    for img_path in img_paths:
        # Load image
        image = cv2.imread(str(img_path))
        if image is None:
            continue
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Load labels
        lbl_path = Path(input_lbl_dir) / f"{img_path.stem}.txt"
        bboxes = []
        class_labels = []
        if lbl_path.exists():
            with open(lbl_path, 'r') as f:
                for line in f.readlines():
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        # YOLO format: x_center, y_center, width, height (normalized)
                        bbox = [float(x) for x in parts[1:5]]
                        bboxes.append(bbox)
                        class_labels.append(class_id)
        
        # Save original first
        orig_img_out = Path(output_img_dir) / f"{img_path.stem}_orig.jpg"
        orig_lbl_out = Path(output_lbl_dir) / f"{img_path.stem}_orig.txt"
        cv2.imwrite(str(orig_img_out), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if bboxes:
            with open(orig_lbl_out, 'w') as f:
                for bbox, cls in zip(bboxes, class_labels):
                    f.write(f"{cls} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")

        # Generate augments
        for i in range(num_augments):
            try:
                transformed = transform(image=image, bboxes=bboxes, class_labels=class_labels)
                aug_img = transformed['image']
                aug_bboxes = transformed['bboxes']
                aug_classes = transformed['class_labels']
                
                aug_img_out = Path(output_img_dir) / f"{img_path.stem}_aug_{i}.jpg"
                aug_lbl_out = Path(output_lbl_dir) / f"{img_path.stem}_aug_{i}.txt"
                
                cv2.imwrite(str(aug_img_out), cv2.cvtColor(aug_img, cv2.COLOR_RGB2BGR))
                
                with open(aug_lbl_out, 'w') as f:
                    for bbox, cls in zip(aug_bboxes, aug_classes):
                        f.write(f"{cls} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")
            except Exception as e:
                print(f"Error augmenting {img_path.name}: {e}")

if __name__ == "__main__":
    print("Starting Data Augmentation Process...")
    # Example usage paths
    INPUT_IMAGES = "data/images/train"
    INPUT_LABELS = "data/labels/train"
    OUTPUT_IMAGES = "data/images/train_aug"
    OUTPUT_LABELS = "data/labels/train_aug"
    
    # augment_dataset(INPUT_IMAGES, INPUT_LABELS, OUTPUT_IMAGES, OUTPUT_LABELS)
    print("Data Augmentation script ready. Configure paths and uncomment to run.")
