"""Resolve the three name fields from the visual zone (VIZ) and MRZ line 1."""
import re
from .core import C2L, L2C
NF = ("Last_name_ru", "First_name_ru", "Middle_name_ru")
FILLER_NOISE = re.compile(r"(?<=<)[A-Z0-9](?=<)")

def _viz_seq(d):
    seq = []
    for i, f in enumerate(NF):
        v = d["viz"].get(f)
        if i == 1: seq += [("<", 1.0, None), ("<", 1.0, None)]
        if v is None:
            if i < 2: return None
            continue
        if i == 2: seq.append(("<", 1.0, None))
        for l in v["lines"]:
            for ch, c in zip(l["text"], l["char_conf"]):
                seq.append(("<" if ch in " -" else ch, c, ch if ch in " -" else None))
    return seq

def resolve_names(d, m, hi=0.99, lo=0.95, max_fix=2):
    """Return (names_dict, n_fixed) or (None, reason)."""
    if not m or not m["l1"].startswith("PNRUS") or len(m["l1"]) != 44: return None, "l1"
    vs = _viz_seq(d)
    if vs is None: return None, "viz_missing"
    body, bc = m["l1"][5:], list(m["c1"][5:])
    n = len(vs)
    if n > 39: return None, "too_long"               # MRZ truncated -> unverifiable
    tail = body[n:]
    # tail must be fillers; allow isolated single-char noise only if it is low-confidence
    for i, ch in enumerate(tail):
        if ch != "<" and not (FILLER_NOISE.search(body[n + i - 1:n + i + 2] if n + i > 0 else "") and bc[n + i] < 0.9):
            return None, "tail"
    if body[n - 1] == "<" if n else True: pass
    fixes = []
    out = []
    for i, ((vch, vc, sep), mch, mc) in enumerate(zip(vs, body[:n], bc[:n])):
        if vch == "<" or mch == "<":
            if vch != mch: return None, "structure"
            out.append(sep or "<"); continue
        vlat = C2L.get(vch.replace("Ё", "Е"))
        if vlat is None: return None, "viz_char"
        mletter = L2C.get(mch)                          # None for 0/1/5 etc. -> MRZ char invalid
        if mch == vlat or (mch == "2" and vch in "ЕЁ"):
            out.append(mletter if mletter else vch); continue
        if mletter is None: mc = 0.0
        if mc < lo and vc >= hi: out.append(vch.replace("Ё", "Е")); fixes.append(i)
        elif vc < lo and mc >= hi: out.append(mletter); fixes.append(i)
        else: return None, "conflict"
    if len(fixes) > max_fix: return None, "many"
    s = "".join(out)
    parts = s.split("<<", 1)
    last = parts[0]; rest = parts[1].split("<", 1)
    first = rest[0]; middle = rest[1] if len(rest) > 1 else ""
    return {"Last_name_ru": last, "First_name_ru": first, "Middle_name_ru": middle}, len(fixes)
