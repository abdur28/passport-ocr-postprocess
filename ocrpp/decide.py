import re
from .pipeline import *
from .textrisk import *
from .snapping import snap
# In birth places these abbreviations always end with a dot in the labels -> a missing dot is an OCR error.
TRAIL_BP = re.compile(r"(^|[\s.])(ОБЛ|РЕСП|КР|Г|ПОС|С|Д|ДЕР|П|Х|ХУТ|СТ|ГОР|РАЙ)$")
# Thresholds chosen by 5-fold CV on train (one notch more conservative than the first non-label-noise error).
P_ORG = dict(t=0.95, to=0.99, mo=1, allow_susp=(4,))
P_BP  = dict(t=0.95, to=0.97, mo=4, allow_susp=(4,))
def text_ok(f, field, p, nm=None):
    if f is None: return False, "missing"
    if nm is not None and any(nm.near(t) for t in f["oov"]): return False, "nearmiss"
    if f["min_conf"] < p["t"]: return False, "lowconf"
    if f["vcover"] <= 0.85 or f["max_gap"] >= 0.5 or abs(f["n_lines"] - f["exp_lines"]) >= 0.6: return False, "lines"
    if f["n_oov"] > p["mo"] or f["oov_minconf"] < p["to"]: return False, "oov"
    if [s for s in f["susp"] if s not in p.get("allow_susp", ())] or f["nodot_abbr"]: return False, "pattern"
    return True, "ok"

def decide(d, vocab, nm=None, org_by_code=None, bp_known=None):
    """Return (fields, reasons). Empty `reasons` means accept."""
    out, info, viz, m = predict(d)
    reasons = []
    if not info["mrz2"]: reasons.append("mrz")
    if not info["names_ok"]: reasons.append("names")
    if info["mrz2"] and not info.get("dates_ok"): reasons.append("dates")
    for F, p in (("Issue_organization_ru", P_ORG), ("Birth_place_ru", P_BP)):
        f = text_features3(d["viz"].get(F), vocab, F)
        ok, why = text_ok(f, F, p, nm)
        if ok and F == "Birth_place_ru" and TRAIL_BP.search(viz[F] or ""): ok, why = False, "trail_abbr"
        if not ok and F == "Issue_organization_ru" and org_by_code is not None and why not in ("missing",):
            s = snap(viz[F], org_by_code.get(out.get("Issue_organisation_code"), ()))
            if s: out[F] = s; ok = True
        if not ok and F == "Birth_place_ru" and bp_known is not None and viz[F] and " ".join(viz[F].split()) in bp_known:
            ok = True
        if not ok: reasons.append(F[:5] + ":" + why)
    if not reasons:
        valid, border = validity(info["birth"], info["issue"])
        if not valid: reasons.append("invalid" + ("_border" if border else ""))
    return out, reasons
