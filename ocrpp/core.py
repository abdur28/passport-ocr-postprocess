import json, re, csv, collections, datetime as dt
FIELDS = ["Last_name_ru", "First_name_ru", "Middle_name_ru", "Sex_ru", "Birth_date",
          "Birth_place_ru", "Issue_date", "Issue_organisation_code", "Licence_number",
          "Issue_organization_ru"]
CYR = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
LAT = "ABVGDE2JZIQKLMNOPRSTUFHC34WXY9678"
C2L = dict(zip(CYR, LAT)); L2C = dict(zip(LAT, CYR))
W = [7, 3, 1]
def _v(c):
    if c.isdigit(): return int(c)
    if c == '<': return 0
    if 'A' <= c <= 'Z': return ord(c) - 55
    return -100
def check(s): return sum(_v(c) * W[i % 3] for i, c in enumerate(s)) % 10

def viz_text(v):
    if not v: return None
    return " ".join(l["text"] for l in v["lines"]).strip()

def to_mrz_name(s):
    """Cyrillic name -> MRZ latin, separators (space, hyphen) -> '<'."""
    out = []
    for ch in s:
        if ch in C2L: out.append(C2L[ch])
        elif ch in " -": out.append("<")
        else: return None
    return "".join(out)

def parse_mrz(m):
    if not m or len(m.get("lines") or []) != 2: return None
    l1, l2 = m["lines"][0]["text"], m["lines"][1]["text"]
    r = {"l1": l1, "l2": l2,
         "c1": m["lines"][0]["char_conf"], "c2": m["lines"][1]["char_conf"]}
    r["l1_ok"] = l1.startswith("PNRUS") and len(l1) == 44 and re.fullmatch(r"[A-Z0-9<]+", l1) is not None
    r["l2_ok"] = len(l2) == 44 and re.fullmatch(r"[0-9]{9}[0-9]RUS[0-9]{6}[0-9][MF]<{7}[0-9]{13}<[0-9]{2}", l2) is not None
    if r["l2_ok"]:
        num, birth, opt = l2[0:9], l2[13:19], l2[28:42]
        r["checks"] = (check(num) == int(l2[9]) and check(birth) == int(l2[19])
                       and check(opt) == int(l2[42])
                       and check(l2[0:10] + l2[13:20] + l2[21:43]) == int(l2[43]))
        r["Licence_number"] = f"{num[0:2]} {num[2]}{opt[0]} {num[3:9]}"
        r["birth"] = birth  # YYMMDD
        r["issue"] = opt[1:7]
        r["Issue_organisation_code"] = f"{opt[7:10]}-{opt[10:13]}"
        r["Sex_ru"] = {"M": "МУЖ.", "F": "ЖЕН."}[l2[20]]
    else:
        r["checks"] = False
    if r["l1_ok"]:
        r["names_body"] = l1[5:]
    return r

DATE_RE = re.compile(r"^(\d\d)\.(\d\d)\.(\d{4})$")
def parse_date(s):
    m = DATE_RE.match(s or "")
    if not m: return None
    try: return dt.date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError: return None
def yymmdd(d): return d.strftime("%y%m%d")

REF_DATE = dt.date(2026, 10, 1)
def add_years(d, n):
    try: return d.replace(year=d.year + n)
    except ValueError: return d.replace(year=d.year + n, day=28)

def validity(birth, issue):
    """Is a RF passport issued on `issue` to a person born `birth` valid on REF_DATE?
    Returns (valid: bool, borderline: bool)."""
    if not birth or not issue: return False, True
    if issue > REF_DATE or issue < add_years(birth, 14): return False, False
    for age in (20, 45):
        b = add_years(birth, age)
        if issue < b <= REF_DATE:            # had to be replaced
            grace_end = b + dt.timedelta(days=90)
            borderline = REF_DATE <= grace_end
            return False, borderline
    return True, False

LOOK = {"O": "0", "D": "0", "Q": "0", "U": "0", "I": "1", "L": "1", "Z": "2", "S": "5",
        "G": "6", "B": "8", "A": "4", "T": "7"}
DIGIT_POS = set(range(0, 10)) | set(range(13, 20)) | set(range(28, 41)) | {42, 43}
L2_RE = re.compile(r"[0-9]{9}[0-9]RUS[0-9]{6}[0-9][MF]<{7}[0-9]{13}<[0-9]{2}")

def _fix_template(s, sex):
    if len(s) != 44: return None
    c = list(s)
    for i in DIGIT_POS:
        if not c[i].isdigit(): c[i] = LOOK.get(c[i], c[i])
    c[10:13] = list("RUS")
    for i in range(21, 28): c[i] = "<"
    c[41] = "<"
    if c[20] not in "MF" and sex: c[20] = sex
    return "".join(c)

def repair_l2(l2, sex_hint=None):
    """Candidate repairs of MRZ line 2: lookalike letters, filler noise, one inserted/deleted char.
    Returns set of repaired strings that match the template and pass all check digits."""
    cands = set()
    srcs = [l2]
    if len(l2) == 45: srcs += [l2[:i] + l2[i + 1:] for i in range(45)]
    if len(l2) == 43:
        for i in range(44):
            for ch in "<0123456789": srcs.append(l2[:i] + ch + l2[i:])
    for s in srcs:
        r = _fix_template(s, sex_hint)
        if not r or not L2_RE.fullmatch(r): continue
        num, birth, opt = r[0:9], r[13:19], r[28:42]
        if (check(num) == int(r[9]) and check(birth) == int(r[19]) and check(opt) == int(r[42])
                and check(r[0:10] + r[13:20] + r[21:43]) == int(r[43])):
            cands.add(r)
    return cands
