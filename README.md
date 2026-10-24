# RF passport OCR post-processing (test task)

`python postprocess.py data/test_predictions.jsonl answers.jsonl` → accept / reject per document with corrected fields.

* `REPORT.md` — approach, findings, forecast for test (RU).
* `answers.jsonl` — answers for test (916 accepted of 2000).
* `ocrpp/` — code: MRZ parsing/repair (`core.py`), name resolution VIZ↔MRZ (`names.py`), text-field risk features (`textrisk.py`), snapping to known strings (`snapping.py`), decision rules (`decide.py`).
* `resources/model.json` — vocabulary and known strings built by `build_resources.py` from train labels + DaData reference.
* `cv_eval.py` — 5-fold cross-validation on train.

Python 3.8+, standard library only, CPU, offline. Input data (`data/`, `reference/`) is not committed — put the task files next to the code.
