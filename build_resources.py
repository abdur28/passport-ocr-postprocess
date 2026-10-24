"""Build resources/model.json from the train labels and the subdivision reference.
Usage: python build_resources.py data/train_labels.jsonl reference/subdivisions.csv resources/model.json"""
import json, sys
from ocrpp.model import build
res = build(sys.argv[1], sys.argv[2])
json.dump(res, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False)
print("vocab", len(res["vocab"]), "codes", len(res["org_by_code"]), "birth places", len(res["bp_known"]))
