\# Larvae Lens Vision Engine V0 — Model Performance



\## Model 1 — Breeding Object Detection



Task: Object Detection



Classes:

\- Bottle

\- Coconut-Exocarp

\- Drain-Inlet

\- Tire

\- Vase



Best epoch: 50



Precision: 88.31%

Recall: 86.13%

mAP@50: 90.38%

mAP@50-95: 67.35%



Checkpoint:

runs/detect/baseline-v1/weights/best.pt





\## Model 2 — Water-in-Container Segmentation



Task: Segmentation



Classes:

\- tire\_with\_water

\- vase\_with\_water



Best epoch: 50



Mask Precision: 68.41%

Mask Recall: 57.34%

Mask mAP@50: 60.63%

Mask mAP@50-95: 36.31%



Box Precision: 73.49%

Box Recall: 52.22%

Box mAP@50: 59.18%

Box mAP@50-95: 35.78%



Checkpoint:

runs/segment/water-seg-v1/weights/best.pt





\## Model 3 — Open Stagnant Water Segmentation



Task: Segmentation



Classes:

\- open\_stagnant\_water

\- water\_in\_container

\- dense\_vegetation\_habitat



Best epoch by mask mAP@50-95: 61



Mask Precision: 62.68%

Mask Recall: 26.83%

Mask mAP@50: 22.57%

Mask mAP@50-95: 11.07%



Box Precision: 62.62%

Box Recall: 26.17%

Box mAP@50: 23.46%

Box mAP@50-95: 11.92%



Checkpoint:

model3\_balanced\_v3/weights/best.pt





\## Model 4 — Mosquito Larvae Detection



Task: Object Detection



Classes:

\- Bukan Jentik

\- Jentik



Best epoch by box mAP@50-95: 89



Precision: 80.65%

Recall: 83.47%

mAP@50: 87.53%

mAP@50-95: 54.77%



Class-specific validation result for Jentik:

Precision: 83.6%

Recall: 90.4%

mAP@50: 91.8%

mAP@50-95: 58.8%



Checkpoint:

runs/detect/model4-larvae-v1/weights/best.pt
