"""5-fold cross-validation on train: resources are rebuilt without the held-out fold.
Usage: python cv_eval.py data/train_predictions.jsonl data/train_labels.jsonl reference/subdivisions.csv [seed]"""
import json, sys, random, collections, csv
from ocrpp.core import FIELDS
from ocrpp.decide import decide
from ocrpp.model import Model
from ocrpp.textrisk import tokens

def norm(s): return " ".join(str(s or "").split()).upper()
def main(pred, lab, ref, seed=0):
    P = [json.loads(l) for l in open(pred, encoding="utf-8")]
    L = {d["doc_id"]: d["fields"] for d in map(json.loads, open(lab, encoding="utf-8"))}
    ids = sorted(L); random.Random(seed).shuffle(ids); fold = {k: i % 5 for i, k in enumerate(ids)}
    refv = collections.Counter()
    for r in csv.DictReader(open(ref, encoding="utf-8")): refv.update(tokens(r["name"]))
    acc = bad = 0; errs = []
    for f in range(5):
        vocab = collections.Counter(refv); obc = collections.defaultdict(set); bpk = set()
        for k, g in L.items():
            if fold[k] == f: continue
            vocab.update(tokens(g["Birth_place_ru"])); vocab.update(tokens(g["Issue_organization_ru"]))
            obc[g["Issue_organisation_code"]].add(" ".join(g["Issue_organization_ru"].split()))
            bpk.add(" ".join(g["Birth_place_ru"].split()))
        m = Model({"vocab": vocab, "org_by_code": obc, "bp_known": bpk})
        for d in P:
            if fold[d["doc_id"]] != f: continue
            out, reasons = decide(d, m.vocab, m.nm, m.org_by_code, m.bp_known)
            if reasons: continue
            acc += 1; g = L[d["doc_id"]]
            wrong = [x for x in FIELDS if norm(out.get(x)) != norm(g[x])]
            if wrong: bad += 1; errs.append((d["doc_id"], [(x, out.get(x), g[x]) for x in wrong]))
    print(f"accepted {acc}/{len(P)} ({acc/len(P):.1%}), accepted with error {bad}")
    for e in errs: print("  ", e)
if __name__ == "__main__":
    main(*sys.argv[1:4], int(sys.argv[4]) if len(sys.argv) > 4 else 0)
