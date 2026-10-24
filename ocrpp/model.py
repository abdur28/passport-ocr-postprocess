"""Resources learned from the training labels + the DaData subdivision reference."""
import json, collections, csv
from .textrisk import tokens, NearMiss

def build(train_labels_path, reference_csv):
    vocab = collections.Counter()
    for r in csv.DictReader(open(reference_csv, encoding="utf-8")):
        vocab.update(tokens(r["name"]))
    org_by_code = collections.defaultdict(set); bp_known = set()
    for line in open(train_labels_path, encoding="utf-8"):
        g = json.loads(line)["fields"]
        vocab.update(tokens(g["Birth_place_ru"])); vocab.update(tokens(g["Issue_organization_ru"]))
        org_by_code[g["Issue_organisation_code"]].add(" ".join(g["Issue_organization_ru"].split()))
        bp_known.add(" ".join(g["Birth_place_ru"].split()))
    return {"vocab": dict(vocab), "org_by_code": {k: sorted(v) for k, v in org_by_code.items()},
            "bp_known": sorted(bp_known)}

class Model:
    def __init__(self, res):
        self.vocab = collections.Counter(res["vocab"])
        self.nm = NearMiss(self.vocab)
        self.org_by_code = {k: set(v) for k, v in res["org_by_code"].items()}
        self.bp_known = set(res["bp_known"])
    @classmethod
    def load(cls, path):
        return cls(json.load(open(path, encoding="utf-8")))
