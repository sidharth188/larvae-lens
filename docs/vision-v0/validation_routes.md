\# Larvae Lens Vision Engine V0 — Functional Validation



\## Objective



The objective of Phase 0 validation was to verify that the Vision Engine correctly executes every predefined decision route.



This validation measures decision-route coverage and functional orchestration. It does not represent overall model accuracy.



\## Decision Routes



| Test | Model 1 | Model 2 | Model 3 | Model 4 | Expected Result |

|------|---------|---------|---------|---------|-----------------|

| T1 | YES | YES | — | YES | biological\_evidence |

| T2 | YES | YES | — | NO | potential\_breeding |

| T3 | NO | — | YES | YES | biological\_evidence |

| T4 | NO | — | YES | NO | potential\_breeding |

| T5 | YES | NO | — | — | garbage |

| T6 | NO | — | NO | — | garbage |



\## Results



All six predefined routes were successfully executed.



Decision-route coverage: 6/6 = 100%



\## T1 — Container + Water + Larvae



Image:

20240701\_125029\_jpg.rf.51df96a345cdcc538c7564e75e80aea0.jpg



Model 1:

Vase × 2

Confidence: 0.8803



Model 2:

vase\_with\_water

Confidence: 0.3084



Model 4:

Jentik × 2

Confidence: 0.6406

Larvae count: 2



Route:

model1\_model2



Result:

biological\_evidence



Validation:

PASS





\## T2 — Container + Water + No Larvae



Image:

360\_F\_798272270\_jpg.rf.92def0de73c32ee4bc4b4e8f26a039c2.jpg



Model 1:

Tire

Confidence: 0.9334



Model 2:

tire\_with\_water

Confidence: 0.9234



Model 4:

No larvae detected



Route:

model1\_model2



Result:

potential\_breeding



Validation:

PASS





\## T3 — Open Stagnant Water + Larvae



Image:

resized\_\_MG\_0001\_JPG.rf.fc111beb43f792bcdbd1f64c9c4ede41.jpg



Model 1:

No breeding object detected



Model 3:

open\_stagnant\_water

Confidence: 0.4332



Model 4:

Jentik × 3

Confidence: 0.7987

Larvae count: 3



Route:

model3



Result:

biological\_evidence



Validation:

PASS





\## T4 — Open Stagnant Water + No Larvae



Image:

C:\\Users\\siddh\\Desktop\\image2006.jpeg



Model 1:

No breeding object detected



Model 3:

open\_stagnant\_water

Confidence: 0.8495



Model 4:

No larvae detected



Route:

model3



Result:

potential\_breeding



Validation:

PASS





\## T5 — Breeding Object Without Water



Model 1:

Tire

Confidence: 0.7859



Model 2:

Water not detected



Model 3:

Not executed



Model 4:

Not executed



Route:

model1\_model2\_failed



Result:

garbage



Validation:

PASS





\## T6 — No Relevant Habitat Detected



Image:

20240916\_125025\_jpg.rf.66bd7fc63e071c77c554754ef51a666f.jpg



Model 1:

No detection

Confidence: 0.0



Model 3:

No detection

Confidence: 0.0



Model 4:

Not executed



Route:

model3\_failed



Result:

garbage



Validation:

PASS





\## Overall Validation



Passed routes: 6/6



Decision-route coverage: 100%



Important:

100% route coverage does not represent 100% model accuracy.

It indicates that all predefined decision paths were successfully exercised during functional validation.
