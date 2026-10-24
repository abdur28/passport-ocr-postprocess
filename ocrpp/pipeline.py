import datetime as dt
from .names import resolve_names
from .core import *

def century_date(yymmdd_s, lo, hi):
    """Pick the century so that date lies in [lo, hi]; None if not unique."""
    c = []
    for cent in (1900, 2000):
        try: d = dt.date(cent + int(yymmdd_s[:2]), int(yymmdd_s[2:4]), int(yymmdd_s[4:6]))
        except ValueError: continue
        if lo <= d <= hi: c.append(d)
    return c[0] if len(c) == 1 else None

def predict(d):
    viz = {f: viz_text(d["viz"].get(f)) for f in FIELDS}
    m = parse_mrz(d.get("mrz"))
    out = {}; info = {"mrz2": bool(m and m["l2_ok"] and m["checks"]), "repaired": False}
    if m and not info["mrz2"]:
        sex_hint = {"МУЖ.": "M", "ЖЕН.": "F"}.get(viz["Sex_ru"] or "")
        cands = repair_l2(m["l2"], sex_hint)
        if len(cands) == 1:
            r = cands.pop(); m2 = dict(m); m2["l2"] = r
            num, opt = r[0:9], r[28:42]
            m2.update(checks=True, l2_ok=True, birth=r[13:19], issue=opt[1:7],
                      Licence_number=f"{num[0:2]} {num[2]}{opt[0]} {num[3:9]}",
                      Issue_organisation_code=f"{opt[7:10]}-{opt[10:13]}",
                      Sex_ru={"M": "МУЖ.", "F": "ЖЕН."}[r[20]])
            m = m2; info["mrz2"] = True; info["repaired"] = True
    names, why = resolve_names(d, m)
    info["names_ok"] = names is not None; info["names_why"] = why
    if names: out.update(names)
    if info["mrz2"]:
        out["Sex_ru"] = m["Sex_ru"]; out["Licence_number"] = m["Licence_number"]
        out["Issue_organisation_code"] = m["Issue_organisation_code"]
        iss = century_date(m["issue"], dt.date(1997, 1, 1), REF_DATE)
        bir = century_date(m["birth"], add_years(iss, -100), add_years(iss, -14)) if iss else None
        # cross-check full year with the visual zone when available
        vb = parse_date(viz["Birth_date"])
        if bir and vb and vb.year % 100 == bir.year % 100 and vb.year != bir.year: bir = None
        info["dates_ok"] = bool(iss and bir)
        if iss: out["Issue_date"] = iss.strftime("%d.%m.%Y")
        if bir: out["Birth_date"] = bir.strftime("%d.%m.%Y")
        info["birth"], info["issue"] = bir, iss
        # agreement with viz (extra evidence)
        info["viz_agree"] = sum(1 for f in ("Sex_ru","Licence_number","Issue_organisation_code","Issue_date","Birth_date")
                                if (viz[f] or "") == out.get(f))
        if info["repaired"] and info["viz_agree"] < 5: info["mrz2"] = False   # repaired MRZ must be confirmed by VIZ
    out["Birth_place_ru"] = viz["Birth_place_ru"]
    out["Issue_organization_ru"] = viz["Issue_organization_ru"]
    return out, info, viz, m
