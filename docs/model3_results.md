# Model 3 — Open Stagnant-Water Segmentation

## Purpose

Model 3 is the third computer-vision component in the Larvae Lens pipeline. Its role is to identify visual habitat evidence that is not dependent on a recognizable breeding container.

The Model 3 classes are:

- `0` — `open_stagnant_water`
- `1` — `water_in_container`
- `2` — `dense_vegetation_habitat`

Model 3 uses YOLO11n-seg for object detection and segmentation.

## Dataset development

The initial Model 3 candidate dataset contained approximately 5,394 images. A representative annotated subset was prepared and then iteratively balanced because the original class distribution was heavily dominated by class 0.

The balanced dataset used for the final training iteration was stored locally at:

`outputs/model3_balanced`

The dataset was intentionally kept outside GitHub together with generated training outputs and model weights.

### Final dataset class counts

| Split | Class 0 | Class 1 | Class 2 |
|---|---:|---:|---:|
| Train | 318 | 5 | 40 |
| Valid | 59 | 5 | 8 |
| Test | 6 | 7 | 6 |

These are **instance counts**, not image counts.

The test set contains 13 images and 19 annotated instances in total.

## Training configuration

The final training run was:

- Model: `yolo11n-seg.pt`
- Task: segmentation
- Epochs requested: 100
- Actual epochs: 81
- Image size: 640
- Batch size: 2
- Device: CUDA GPU 0
- Workers: 0
- Patience: 20
- Optimizer: Ultralytics automatic optimizer selection
- GPU: NVIDIA GeForce GTX 1650, 4 GB
- Python: 3.10
- PyTorch: 2.11.0+cu128
- Ultralytics: 8.4.120

Early stopping stopped training at epoch 81. The best checkpoint was obtained at epoch 61.

Best weights were saved locally as:

`runs/model3_balanced_v3/weights/best.pt`

## Validation results

The best checkpoint (`best.pt`) produced the following validation results:

| Class | Box Precision | Box Recall | Box mAP50 | Box mAP50-95 | Mask Precision | Mask Recall | Mask mAP50 | Mask mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All | 0.627 | 0.262 | 0.235 | 0.119 | 0.628 | 0.268 | 0.226 | 0.111 |
| open_stagnant_water | 0.497 | 0.535 | 0.471 | 0.239 | 0.514 | 0.555 | 0.489 | 0.251 |
| water_in_container | 1.000 | 0.000 | 0.0458 | 0.0221 | 1.000 | 0.000 | 0.0050 | 0.0010 |
| dense_vegetation_habitat | 0.385 | 0.250 | 0.187 | 0.0958 | 0.370 | 0.250 | 0.183 | 0.0798 |

The validation set had 73 images and 72 instances.

## Independent test results

The best checkpoint was also evaluated on the held-out test split containing 13 images and 19 instances.

| Class | Box Precision | Box Recall | Box mAP50 | Box mAP50-95 | Mask Precision | Mask Recall | Mask mAP50 | Mask mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All | 0.512 | 0.325 | 0.263 | 0.105 | 0.513 | 0.389 | 0.243 | 0.0544 |
| open_stagnant_water | 0.216 | 0.500 | 0.289 | 0.0976 | 0.177 | 0.500 | 0.288 | 0.0526 |
| water_in_container | 1.000 | 0.000 | 0.124 | 0.0347 | 1.000 | 0.000 | 0.0672 | 0.00852 |
| dense_vegetation_habitat | 0.321 | 0.474 | 0.375 | 0.182 | 0.361 | 0.667 | 0.373 | 0.102 |

## Interpretation

Model 3 is currently usable as an experimental component of the Larvae Lens vision pipeline, but it is **not yet a high-accuracy production detector**.

The strongest class is `open_stagnant_water`, with test mask mAP50 of approximately 0.288 and recall of 0.500. The `water_in_container` class has zero recall on the test set, so the current Model 3 should not be relied upon to independently detect that class.

The results also show why Model 3 should be evaluated as one component of the larger decision pipeline rather than treated as a standalone mosquito-risk classifier.

## Role in the Larvae Lens pipeline

Model 3 is used when Model 1 does not identify a recognized breeding object, providing an alternative route for detecting potential habitat:

```text
IMAGE
  |
  +--> Model 1: Breeding object?
  |       |
  |       +--> YES --> Model 2: Water in object?
  |       |                 |
  |       |                 +--> YES --> Model 4: Larvae
  |       |
  |       +--> NO --> Model 3: Open stagnant water / habitat
  |                         |
  |                         +--> YES --> Model 4: Larvae
  |
  +--> If required visual evidence is not detected --> Wrong photo / garbage data
```

After Model 4, the pipeline separates biological evidence from potential breeding evidence and passes the evidence to the later risk-engine stage.

## Current status

**Model 3 training: complete for the current prototype iteration.**

Next engineering step: integrate Models 1–3 into **Vision Engine V0** before proceeding to Model 4 (mosquito larvae detection).
