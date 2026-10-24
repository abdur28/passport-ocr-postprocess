"""Post-processing of RF passport OCR: accept (with corrected fields) or reject each document.
Usage: python postprocess.py data/test_predictions.jsonl answers.jsonl [--explain reasons.jsonl]
CPU only, no network. Uses resources/model.json (see build_resources.py)."""
import json, sys, os, collections
from ocrpp.core import FIELDS
from ocrpp.decide import decide
from ocrpp.model import Model

def main(inp, outp, explain=None):
    here = os.path.dirname(os.path.abspath(__file__))
    model = Model.load(os.path.join(here, "resources", "model.json"))
    stats = collections.Counter()
    ex = open(explain, "w", encoding="utf-8") if explain else None
    with open(inp, encoding="utf-8") as fi, open(outp, "w", encoding="utf-8") as fo:
        for line in fi:
            d = json.loads(line)
            fields, reasons = decide(d, model.vocab, model.nm, model.org_by_code, model.bp_known)
            if reasons:
                rec = {"doc_id": d["doc_id"], "decision": "reject"}
                for r in reasons: stats[r] += 1
            else:
                rec = {"doc_id": d["doc_id"], "decision": "accept",
                       "fields": {f: fields.get(f) or "" for f in FIELDS}}
            stats[rec["decision"]] += 1
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if ex: ex.write(json.dumps({"doc_id": d["doc_id"], "reasons": reasons}, ensure_ascii=False) + "\n")
    n = stats["accept"] + stats["reject"]
    print(f"documents {n}: accept {stats['accept']} ({stats['accept']/n:.1%}), reject {stats['reject']}", file=sys.stderr)
    print("reject reasons (a document can have several):", file=sys.stderr)
    for r, c in stats.most_common():
        if r not in ("accept", "reject"): print(f"  {r:22s} {c}", file=sys.stderr)

if __name__ == "__main__":
    a = sys.argv[1:]
    exp = None
    if "--explain" in a: i = a.index("--explain"); exp = a[i + 1]; a = a[:i] + a[i + 2:]
    main(a[0], a[1], exp)
