\# Larvae Lens Vision Engine V0 — Dataset Description



\## 1. Overview



Larvae Lens Vision Engine V0 consists of four specialized computer-vision models. Separate datasets were used because each model performs a different visual task in the multi-stage vision pipeline.



| Model | Purpose | Task | Classes |

|---|---|---|---|

| Model 1 | Breeding-object identification | Object Detection | Bottle, Coconut-Exocarp, Drain-Inlet, Tire, Vase |

| Model 2 | Water within containers | Segmentation | tire\_with\_water, vase\_with\_water |

| Model 3 | Open stagnant-water habitat | Segmentation | open\_stagnant\_water, water\_in\_container, dense\_vegetation\_habitat |

| Model 4 | Mosquito-larvae identification | Object Detection | Bukan Jentik, Jentik |



\---



\# 2. Model 1 — Breeding Object Detection



\## Dataset



Location:



LarvaeLensData/Breeding Place Detection



Task:



Object Detection



Classes:



0\. Bottle

1\. Coconut-Exocarp

2\. Drain-Inlet

3\. Tire

4\. Vase



\## Dataset Statistics



| Split | Images | Labels | Annotations |

|---|---:|---:|---:|

| Train | 3,871 | 3,871 | 8,125 |

| Validation | 371 | 371 | 731 |

| Test | 183 | 183 | 424 |

| Total | 4,425 | 4,425 | 9,280 |



\## Class Distribution



| Class | Train | Validation | Test |

|---|---:|---:|---:|

| Bottle | 1,194 | 100 | 50 |

| Coconut-Exocarp | 1,939 | 171 | 101 |

| Drain-Inlet | 1,164 | 135 | 54 |

| Tire | 1,635 | 119 | 115 |

| Vase | 2,193 | 206 | 104 |



\---



\# 3. Model 2 — Water-in-Container Segmentation



\## Dataset



Location:



LarvaeLensData/Water Surface Segmentation



Task:



Segmentation



Classes:



0\. tire\_with\_water

1\. vase\_with\_water



\## Dataset Statistics



| Split | Images | Labels | Annotations |

|---|---:|---:|---:|

| Train | 286 | 286 | 533 |

| Validation | 30 | 30 | 43 |

| Test | 15 | 15 | 31 |

| Total | 331 | 331 | 607 |



\## Class Distribution



| Class | Train | Validation | Test |

|---|---:|---:|---:|

| tire\_with\_water | 142 | 18 | 7 |

| vase\_with\_water | 391 | 25 | 24 |



\---



\# 4. Model 3 — Open Stagnant Water Segmentation



\## Dataset



The Model 3 dataset was collected and prepared specifically for the open-stagnant-water habitat detection stage.



Dataset:



outputs/model3\_balanced



Task:



Segmentation



Classes:



0\. open\_stagnant\_water

1\. water\_in\_container

2\. dense\_vegetation\_habitat



\## Dataset Statistics



| Split | Images | Labels | Annotations |

|---|---:|---:|---:|

| Train | 336 | 336 | 364 |

| Validation | 73 | 73 | 72 |

| Test | 13 | 13 | 19 |

| Total | 422 | 422 | 455 |



\## Class Distribution



| Class | Train | Validation | Test |

|---|---:|---:|---:|

| open\_stagnant\_water | 318 | 59 | 6 |

| water\_in\_container | 5 | 5 | 7 |

| dense\_vegetation\_habitat | 40 | 8 | 6 |



The dataset exhibits substantial class imbalance. In particular, the water\_in\_container class contains only five training annotations and five validation annotations.



This limitation is considered an important baseline finding for future dataset expansion and model optimization.



\## Training Configuration



Model:



YOLO11n-seg



Input image size:



640 × 640



Batch size:



2



Configured epochs:



100



Pretrained:



Yes



AMP:



Enabled



Deterministic:



Yes



Seed:



0



\## Training Augmentation



HSV hue:



0.015



HSV saturation:



0.7



HSV value:



0.4



Translation:



0.1



Scale:



0.5



Horizontal flip:



0.5



Vertical flip:



0.0



Mosaic:



1.0



MixUp:



0.0



CutMix:



0.0



AutoAugment:



RandAugment



Random erasing:



0.4



Rotation:



0.0



Shear:



0.0



Perspective:



0.0



\---



\# 5. Model 4 — Mosquito Larvae Detection



\## Dataset



Location:



LarvaeLensData/Model4\_Larvae



Task:



Object Detection



Classes:



0\. Bukan Jentik

1\. Jentik



\## Dataset Statistics



| Split | Images | Labels | Annotations |

|---|---:|---:|---:|

| Train | 5,583 | 5,583 | 22,611 |

| Validation | 530 | 530 | 2,233 |

| Test | 261 | 261 | 1,122 |

| Total | 6,374 | 6,374 | 25,966 |



\## Class Distribution



| Class | Train | Validation | Test |

|---|---:|---:|---:|

| Bukan Jentik | 13,768 | 1,320 | 656 |

| Jentik | 8,843 | 913 | 466 |



\---



\# 6. Dataset Preparation Summary



The four datasets were prepared independently according to the requirements of their respective computer-vision tasks. Models 1 and 4 use object-detection annotations, while Models 2 and 3 use segmentation annotations.



The Model 3 dataset was specifically collected and prepared for the open-stagnant-water stage. Its class distribution reveals a substantial imbalance, particularly for the water\_in\_container category. This limitation provides an important direction for subsequent dataset expansion and Vision Engine development.



Exact acquisition metadata such as camera hardware, geographic collection locations, collection dates, and annotation personnel are not included in this V0 record unless separately documented in the experimental records.
