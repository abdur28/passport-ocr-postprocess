"""Snap an uncertain OCR string to a known label string (same subdivision code) when it is within 2 edits."""
import collections
def lev(a, b, cap=4):
    if abs(len(a) - len(b)) > cap: return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b); best = i
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)); best = min(best, cur[j])
        if best > cap: return cap + 1
        prev = cur
    return prev[-1]

def snap(ocr, cands, max_d=2, margin=3):
    if not ocr or not cands: return None
    o = " ".join(ocr.split())
    ds = sorted((lev(o, c), c) for c in cands)
    best, bc = ds[0]; second = ds[1][0] if len(ds) > 1 else 99
    if best <= max_d and second - best >= margin: return bc
    return None
