import re, csv, collections, statistics
from .core import *
TOK = re.compile(r"[А-ЯЁA-Z0-9]+")
def tokens(s): return TOK.findall(s.upper())

def ref_vocab(path="reference/subdivisions.csv"):
    v = collections.Counter()
    for r in csv.DictReader(open(path, encoding="utf-8")):
        v.update(tokens(r["name"]))
    return v

SUSP = [re.compile(p) for p in [
    r"[А-ЯЁ][0-9]|[0-9][А-ЯЁ]",      # digit glued to cyrillic letter (except '-1' handled by hyphen)
    r"[A-Z]",                         # latin letter
    r"(.)\1\1",                       # triple char
    r"Ё",                             # Ё (labels mostly use Е)
    r"\.[А-ЯЁ]",                      # any period glued to a letter (allowed for 1-letter abbr.)
    r"[^А-ЯЁ0-9 .,\-()№\"/]",         # odd symbol
    r"\s[.,]",                         # space before punctuation
    r"^[^А-ЯЁ0-9(]|[^А-ЯЁ0-9.)]$",     # odd start / end
    r"[ЬЪЫ][А-ЯЁ]*\b(?<=^)|\b[ЬЪЫ]",   # word starting with Ь/Ъ/Ы
    r"[АЕЁИОУЫЭЮЯ][ЬЪ]",              # vowel + soft/hard sign
    r"[ЙЬЪ]{2}",
    r"[А-ЯЁ]{2,}\.[А-ЯЁ]",            # 11: multi-letter abbreviation glued to next word (ОБЛ.В) -> label usually has a space
]]

def text_features(v, vocab, field):
    f = {}
    if not v or not v["lines"]:
        return None
    lines = v["lines"]; txt = " ".join(l["text"] for l in lines)
    cc = [c for l in lines for c in l["char_conf"]]
    f["min_conf"] = min(cc) if cc else 0
    f["n_low99"] = sum(c < 0.99 for c in cc)
    f["n_low999"] = sum(c < 0.999 for c in cc)
    f["field_conf"] = v["conf"]
    fb = v["box"]
    top = min(l["box"][1] for l in lines); bot = max(l["box"][1] + l["box"][3] for l in lines)
    f["vcover"] = (bot - top) / max(fb[3], 1)
    f["top_gap"] = (top - fb[1]) / max(fb[3], 1)
    f["bot_gap"] = (fb[1] + fb[3] - bot) / max(fb[3], 1)
    lh = statistics.median(l["box"][3] for l in lines)
    f["exp_lines"] = fb[3] / max(lh, 1)
    f["n_lines"] = len(lines)
    # char width consistency per line
    dens = [l["box"][2] / max(len(l["text"]), 1) / max(l["box"][3], 1) for l in lines]
    f["dens_min"], f["dens_max"] = min(dens), max(dens)
    # horizontal coverage: widest line vs field width
    f["hcover"] = max(l["box"][2] for l in lines) / max(fb[2], 1)
    toks = tokens(txt)
    oov = [t for t in toks if vocab.get(t, 0) == 0 and not t.isdigit()]
    f["n_oov"] = len(oov); f["oov"] = oov
    f["rare"] = sum(1 for t in toks if 0 < vocab.get(t, 0) < 3)
    f["susp"] = [i for i, p in enumerate(SUSP) if p.search(txt)]
    f["len"] = len(txt)
    return f

ABBR_NEED_DOT = set("ГСПДХАНКМ")   # one-letter settlement abbreviations normally followed by '.'
def text_features2(v, vocab, field):
    f = text_features(v, vocab, field)
    if f is None: return None
    lines = sorted(v["lines"], key=lambda l: l["box"][1])
    gaps = [(b["box"][1] - (a["box"][1] + a["box"][3])) / max(a["box"][3], 1) for a, b in zip(lines, lines[1:])]
    f["max_gap"] = max(gaps) if gaps else 0
    # per-token min conf for OOV tokens
    oov_conf = []
    for l in v["lines"]:
        for m in TOK.finditer(l["text"].upper()):
            t = m.group()
            if vocab.get(t, 0) == 0 and not t.isdigit():
                oov_conf.append(min(l["char_conf"][m.start():m.end()]))
    f["oov_minconf"] = min(oov_conf) if oov_conf else 1.0
    txt = " ".join(l["text"] for l in v["lines"])
    f["nodot_abbr"] = bool(re.search(r"(^|\s)[" + "".join(ABBR_NEED_DOT) + r"](\s|$)", txt)) and field == "Birth_place_ru"
    return f

class NearMiss:
    """Detect tokens that are 1 edit (or 2 for long tokens) from a frequent vocabulary word."""
    def __init__(self, vocab, min_count=5):
        self.freq = {w for w, c in vocab.items() if c >= min_count and len(w) >= 3}
        self.dels = collections.defaultdict(set)
        for w in self.freq:
            for d in self._deletes(w): self.dels[d].add(w)
    @staticmethod
    def _deletes(w):
        return {w[:i] + w[i + 1:] for i in range(len(w))} | {w}
    def near(self, t):
        if t in self.freq or len(t) < 3: return None
        for d in self._deletes(t):
            for w in self.dels.get(d, ()):
                if w != t and abs(len(w) - len(t)) <= 1:
                    return w
        return None

def correct_org(txt, vocab, nm, min_freq=20):
    """Replace OOV tokens that are 1 edit from a frequent vocabulary word. Returns (text, corrected_tokens)."""
    fixed = txt; done = set()
    for m in list(TOK.finditer(txt.upper())):
        t = m.group()
        if vocab.get(t, 0) or t.isdigit() or len(t) < 4: continue
        cands = set()
        for dd in nm._deletes(t):
            for w in nm.dels.get(dd, ()):
                if w != t and abs(len(w) - len(t)) <= 1 and vocab[w] >= min_freq: cands.add(w)
        cands = sorted(cands, key=lambda w: -vocab[w])
        if not cands: continue
        if len(cands) > 1 and vocab[cands[1]] * 5 > vocab[cands[0]]: return None, None   # ambiguous
        fixed = re.sub(r"(?<![А-ЯЁA-Z0-9])" + re.escape(t) + r"(?![А-ЯЁA-Z0-9])", cands[0], fixed)
        done.add(t)
    return fixed, done

def text_features3(v, vocab, field, ignore=()):
    """Like text_features2 but chars of `ignore` tokens don't count towards min_conf / OOV."""
    f = text_features2(v, vocab, field)
    if f is None or not ignore: return f
    cc = []
    for l in v["lines"]:
        mask = [True] * len(l["text"])
        for m in TOK.finditer(l["text"].upper()):
            if m.group() in ignore:
                for i in range(m.start(), m.end()): mask[i] = False
        cc += [c for c, k in zip(l["char_conf"], mask) if k]
    f["min_conf"] = min(cc) if cc else 0
    f["oov"] = [t for t in f["oov"] if t not in ignore]; f["n_oov"] = len(f["oov"])
    return f
