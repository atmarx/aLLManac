#!/usr/bin/env python3
"""The disaster-recovery sheets — the three secrets a rebuild can't do without, on paper.

    dr_sheet.py sheet OUT.pdf          print-ready PDF: the unseal key + both backup passwords
    dr_sheet.py phrase FILE            a new 12-word backup password, written to FILE (0600)
    dr_sheet.py words WHAT [FILE]      type a sheet's words back; WHAT is unseal | data | secrets

Words are BIP39 (scripts/bip39-english.txt, the canonical list — its hash is
checked on every run).  A 32-byte unseal key is exactly 24 words; a 128-bit
password is 12.  The last word carries a checksum, so a mistyped word is
refused rather than becoming a wrong key, and the first four letters of any
word identify it.

Run from the repo root (the justfile does).  Host python3, stdlib only: the
day this runs for real may be the day nothing else on the box works.  Nothing
here prints a secret to the terminal — the sheet goes to a file, the words come
in without echo, and the only thing shown about a secret is an 8-hex
fingerprint for matching paper to box.
"""
import base64
import datetime
import getpass
import hashlib
import os
import socket
import subprocess
import sys
import zlib
from pathlib import Path

WORDLIST = Path(__file__).with_name("bip39-english.txt")
WORDLIST_SHA256 = "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"


def _words():
    raw = WORDLIST.read_bytes()
    if hashlib.sha256(raw).hexdigest() != WORDLIST_SHA256:
        sys.exit(f"{WORDLIST} is not the BIP39 English list (hash mismatch) — refusing to encode with it")
    words = raw.decode().split()
    assert len(words) == 2048
    return words


WORDS = _words()
INDEX = {w: i for i, w in enumerate(WORDS)}
PREFIX = {w[:4]: w for w in WORDS}     # BIP39 guarantees the first four letters are unique


# ---- BIP39 ------------------------------------------------------------------

def encode(entropy: bytes) -> list[str]:
    if len(entropy) not in (16, 20, 24, 28, 32):
        raise ValueError(f"{len(entropy)} bytes can't be a BIP39 phrase")
    cs = len(entropy) * 8 // 32
    bits = int.from_bytes(entropy, "big") << cs | hashlib.sha256(entropy).digest()[0] >> (8 - cs)
    n = (len(entropy) * 8 + cs) // 11
    return [WORDS[bits >> (11 * (n - 1 - i)) & 2047] for i in range(n)]


def decode(words: list[str]) -> bytes:
    """Words (or their first four letters) back to bytes; raises ValueError on a bad word or checksum."""
    full = []
    for i, w in enumerate(words, 1):
        w = w.strip().lower()
        if w in INDEX:
            full.append(w)
        elif len(w) >= 4 and PREFIX.get(w[:4], "").startswith(w):
            full.append(PREFIX[w[:4]])
        else:
            raise ValueError(f"word {i}, {w!r}, isn't on the list")
    n = len(full)
    if n not in (12, 15, 18, 21, 24):
        raise ValueError(f"{n} words — a sheet has 12 or 24")
    bits = 0
    for w in full:
        bits = bits << 11 | INDEX[w]
    cs = n * 11 // 33
    ent = (bits >> cs).to_bytes((n * 11 - cs) // 8, "big")
    if bits & ((1 << cs) - 1) != hashlib.sha256(ent).digest()[0] >> (8 - cs):
        raise ValueError("the checksum doesn't match — a word is wrong or out of order")
    return ent


def as_phrase(secret: str) -> list[str] | None:
    """The words, if `secret` is already a BIP39 phrase exactly as `phrase` writes one."""
    words = secret.split(" ")
    try:
        decode(words)
    except ValueError:
        return None
    return words if all(w in INDEX for w in words) else None


def fingerprint(secret: bytes) -> str:
    h = hashlib.sha256(secret).hexdigest()
    return f"{h[:4]} {h[4:8]}"


# ---- What the box holds ------------------------------------------------------

def envfile(path) -> dict:
    out = {}
    try:
        lines = Path(path).read_text().splitlines()
    except FileNotFoundError:
        return out
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out.setdefault(k.strip(), v)        # first wins, like `grep | head -1`
    return out


def unseal_key() -> bytes | None:
    v = envfile(".env").get("BAO_UNSEAL_KEY", "")
    return base64.b64decode(v) if v else None


def backup_password(which: str) -> str | None:
    """Exactly what `just backup` hands restic: the command's or file's output,
    trailing newlines stripped (bash's `$(...)`)."""
    env = envfile("site/backup.env")
    cmd, f = env.get(f"BACKUP_{which}_PASSWORD_COMMAND", ""), env.get(f"BACKUP_{which}_PASSWORD_FILE", "")
    if cmd:
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True).stdout.rstrip("\n")
    if f:
        return Path(f).read_text().rstrip("\n")
    return None


def _create(path, data: bytes):
    """A new file, 0600 — never over one that exists: a secret file is replaced on purpose, by hand."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        sys.exit(f"{path} already exists — left alone.  Move it aside first if replacing it is the point.")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


# ---- A PDF with nothing but the standard fonts -------------------------------

# Helvetica's advance widths (AFM, per 1000 em) for ASCII 32..126 — enough to wrap a paragraph.
_HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
         556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
         1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
         667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
         333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
         556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]


def _width(s, size):
    return sum(_HELV[ord(c) - 32] if 32 <= ord(c) < 127 else (1000 if c == "—" else 556) for c in s) * size / 1000


def _pdfstr(s):
    b = s.encode("cp1252")
    return b"(" + b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


class Page:
    W, H, M = 612, 792, 54           # US Letter, 3/4-inch margins

    def __init__(self):
        self.ops, self.y = [], self.H - self.M

    def text(self, x, y, s, font="F1", size=10):
        self.ops.append(b"BT /%s %g Tf %g %g Td " % (font.encode(), size, x, y) + _pdfstr(s) + b" Tj ET")

    def line(self, s, font="F1", size=10, gap=None):
        self.y -= gap if gap is not None else size * 1.45
        self.text(self.M, self.y, s, font, size)

    def para(self, s, size=10, indent=0):
        words, cur = s.split(" "), ""
        for w in words:
            trial = f"{cur} {w}" if cur else w
            if _width(trial, size) > self.W - 2 * self.M - indent and cur:
                self.y -= size * 1.4
                self.text(self.M + indent, self.y, cur, "F1", size)
                cur = w
            else:
                cur = trial
        if cur:
            self.y -= size * 1.4
            self.text(self.M + indent, self.y, cur, "F1", size)

    def rule(self, y, w=0.5):
        self.ops.append(b"%g w %g %g m %g %g l S" % (w, self.M, y, self.W - self.M, y))

    def box(self, x, y, w, h):
        self.ops.append(b"1 w %g %g %g %g re S" % (x, y, w, h))


def write_pdf(pages, path):
    fonts = {"F1": "Helvetica", "F2": "Helvetica-Bold", "F3": "Courier-Bold", "F4": "Courier"}
    objs = [None, None]                                 # 1 catalog, 2 page tree
    font_ref = {}
    for k, base in fonts.items():
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding /WinAnsiEncoding >>" % base.encode())
        font_ref[k] = len(objs)
    fres = b" ".join(b"/%s %d 0 R" % (k.encode(), n) for k, n in font_ref.items())
    kids = []
    for p in pages:
        body = zlib.compress(b"\n".join(p.ops))
        objs.append(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(body) + body + b"\nendstream")
        content = len(objs)
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources << /Font << %s >> >> /Contents %d 0 R >>"
                    % (Page.W, Page.H, fres, content))
        kids.append(len(objs))
    objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % k for k in kids), len(kids))
    out, offsets = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    _create(path, bytes(out))


# ---- The sheets --------------------------------------------------------------

SHEETS = {
    "unseal": {
        "title": "OpenBao unseal key",
        "opens": "The escrow — every API key the platform has minted for a course or a student — once its data is back on a disk.  An escrow restored from the data bundle's snapshot comes up sealed, and these words open it.  They also mint a new root token (bao operator generate-root), so the root token never needs a sheet of its own.",
        "not": "The backups.  Each bundle takes its own password, on its own page.",
        "use": "On the rebuilt box, in the repo.  Type the 24 words in order with spaces between.  The first writes BAO_UNSEAL_KEY into .env — only if .env has none — and the second opens the escrow:",
        "cmds": ["just dr-words unseal", "just bao-unseal"],
        "check": "On the live box, the same command says whether these words match the key the box runs on, and changes nothing.",
        "replace": "When the escrow is initialized again (bao-init on an empty vault) or its key is rotated (bao operator rekey).  An old sheet opens nothing.",
    },
    "data": {
        "title": "Backup password — the data bundle",
        "opens": "Every database dump (chats, the ledger, identity), the escrow's snapshot and its audit log, uploads, images, and the edge's certificates.  The escrow inside it stays sealed until the unseal-key page opens it.",
        "not": "The secrets bundle (.env and each course's keys) — that is the other password.",
        "use": "The password is the twelve words in order, lowercase, one space between — restic compares the whole string.  This writes it to FILE (mode 600), for BACKUP_DATA_PASSWORD_FILE in site/backup.env:",
        "cmds": ["just dr-words data FILE"],
        "check": "On the live box, the same command without FILE says whether these words match the password the nightly run uses, and changes nothing.",
        "replace": "When the repository's password changes (restic key add, then key remove for the old one).",
    },
    "secrets": {
        "title": "Backup password — the secrets bundle",
        "opens": ".env (every secret on the box, the unseal key among them), each course's fleet/<slug>.env, and site/.  With the data bundle, it is everything a rebuild needs.",
        "not": "The data bundle — no chats, no ledger, no escrow.  That is the other password.",
        "use": "The password is the twelve words in order, lowercase, one space between — restic compares the whole string.  This writes it to FILE (mode 600), for BACKUP_SECRETS_PASSWORD_FILE in site/backup.env:",
        "cmds": ["just dr-words secrets FILE"],
        "check": "On the live box, the same command without FILE says whether these words match the password the nightly run uses, and changes nothing.",
        "replace": "When the repository's password changes (restic key add, then key remove for the old one).",
    },
}
PAIRING = "Store the data page apart from the other two.  Data + secrets is the whole platform, and data + unseal is every escrowed key; secrets + unseal alone opens nothing new."


LITERAL = {
    "use": "Copy it into a file exactly as printed — no spaces before or after — then chmod 600 the file and point the bundle's PASSWORD_FILE line in site/backup.env at it.  dr-words reads word sheets only, so there is no checksum here: check each character.",
    "cmds": [],
    "check": "Better: replace it with a phrase (just dr-phrase FILE, then restic key add with the new one and key remove for the old) and print a word sheet.",
}


def render(kind, words, literal, meta, n, total):
    s, p = SHEETS[kind], Page()
    if not words:
        s = {**s, **LITERAL}
    p.text(p.M, p.y - 10, f"{meta['platform']} — disaster-recovery sheet", "F2", 11)
    p.text(p.W - p.M - 60, p.y - 10, f"page {n} of {total}", "F1", 9)
    p.y -= 14
    p.line(s["title"], "F2", 20, gap=26)
    p.line(f"Box {meta['host']} · {meta['chat']}" + (f" · repository {meta['repo']}" if meta.get("repo") else ""), "F1", 9, gap=16)
    p.line(f"Printed {meta['date']} · fingerprint {meta['fp']}", "F1", 9)
    p.rule(p.y - 10)
    p.y -= 18

    if words:
        cols, rows = 3, (len(words) + 2) // 3
        cw, rh, top = (p.W - 2 * p.M) / cols, 25, p.y - 6
        p.box(p.M, top - rows * rh - 8, p.W - 2 * p.M, rows * rh + 8)
        for i, w in enumerate(words):
            c, r = divmod(i, rows)               # down each column: 1-8 | 9-16 | 17-24
            x, y = p.M + 14 + c * cw, top - (r + 1) * rh + 6
            p.text(x, y, f"{i + 1:>2}", "F4", 10)
            p.text(x + 26, y, w, "F3", 16)
        p.y = top - rows * rh - 8
    else:
        p.y -= 8
        chunks = [literal[i:i + 40] for i in range(0, len(literal), 40)]
        p.box(p.M, p.y - len(chunks) * 24 - 10, p.W - 2 * p.M, len(chunks) * 24 + 10)
        for ch in chunks:
            p.y -= 24
            p.text(p.M + 14, p.y, ch, "F3", 15)
        p.y -= 10
        p.line("Not a word phrase: copy it exactly, character for character.", "F1", 9, gap=16)

    for head, key in (("What it opens", "opens"), ("What it does not open", "not"),
                      ("Using it", "use"), ("Replacing it", "replace")):
        p.line(head, "F2", 11, gap=19)
        p.para(s[key])
        if key == "use":
            for c in s["cmds"]:
                p.line(c, "F3", 11, gap=17)
            p.y -= 3 if s["cmds"] else 0
            p.para(s["check"])
    p.line("Keeping it", "F2", 11, gap=19)
    p.para(PAIRING)
    if p.y < p.M + 70:
        raise RuntimeError(f"the {kind} sheet runs {p.M + 70 - p.y:.0f}pt past its page — shorten its text")

    p.text(p.M, p.M + 52, "Copy ____ of ____      Kept at ______________________________________      Initials ______", "F1", 10)
    p.rule(p.M + 22)
    foot = "BIP39 English words: the first four letters of each are enough, and the last word is a checksum.  Destroy a sheet the moment it's replaced."
    p.text(p.M, p.M + 8, foot if words else "Destroy a sheet the moment it's replaced.", "F1", 8)
    return p


def cmd_sheet(out):
    env = envfile(".env")
    meta = {"platform": env.get("PLATFORM_NAME") or "aLLManac", "host": socket.gethostname().split(".")[0],
            "chat": env.get("CHAT_HOST") or "(no CHAT_HOST)", "date": datetime.date.today().isoformat()}
    benv = envfile("site/backup.env")
    pages, notes = [], []

    key = unseal_key()
    if key is None:
        sys.exit("no BAO_UNSEAL_KEY in .env — nothing to print (just bao-init first)")
    secrets = [("unseal", encode(key), None, key, None)]
    for kind in ("data", "secrets"):
        try:
            pw = backup_password(kind.upper())
        except (OSError, subprocess.CalledProcessError) as e:
            sys.exit(f"the {kind} bundle's password couldn't be read: {e}")
        if not pw:
            notes.append(f"  {kind:<8} no password in site/backup.env — no page")
            continue
        words = as_phrase(pw)
        if not words:
            notes.append(f"  {kind:<8} printed character for character — not a word phrase (just dr-phrase makes one)")
        secrets.append((kind, words, None if words else pw, pw.encode(), benv.get(f"BACKUP_{kind.upper()}_REPO")))

    for n, (kind, words, literal, raw, repo) in enumerate(secrets, 1):
        pages.append(render(kind, words, literal, {**meta, "fp": fingerprint(raw), "repo": repo}, n, len(secrets)))
    write_pdf(pages, out)
    for kind, _w, _l, raw, _r in secrets:
        print(f"  {kind:<8} fingerprint {fingerprint(raw)}")
    for n in notes:
        print(n)
    print(f"\n{len(pages)} page(s) → {out}\nPrint it, check one page with `just dr-words`, then delete the file.")


def cmd_phrase(path):
    words = encode(os.urandom(16))
    _create(path, (" ".join(words) + "\n").encode())
    print(f"12 words → {path}  (fingerprint {fingerprint(' '.join(words).encode())})")


def read_words(n):
    if sys.stdin.isatty():
        typed = getpass.getpass(f"the {n} words, in order (not echoed): ")
    else:
        typed = sys.stdin.read()
    # Tolerate what people actually type off a sheet: numbers, commas, line breaks.
    return [w for w in typed.replace(",", " ").replace(".", " ").split() if not w.isdigit()]


def cmd_words(what, path=None):
    if what not in SHEETS:
        sys.exit("what: unseal | data | secrets")
    try:
        secret = decode(read_words(24 if what == "unseal" else 12))
    except ValueError as e:
        sys.exit(f"refused: {e}")
    if what == "unseal":
        if len(secret) != 32:
            sys.exit("refused: an unseal-key sheet has 24 words — that looks like a password sheet")
        live = unseal_key()
        if live is not None:
            same = live == secret
            print(f"  {'matches' if same else 'DOES NOT MATCH'} the key in .env (sheet {fingerprint(secret)}, .env {fingerprint(live)})")
            if not same:
                print("  .env left alone — remove its BAO_UNSEAL_KEY line first if the sheet is the one to trust")
            sys.exit(0 if same else 1)
        text = Path(".env").read_text() if Path(".env").exists() else ""
        line = "BAO_UNSEAL_KEY=" + base64.b64encode(secret).decode()
        lines = text.splitlines()
        if "BAO_UNSEAL_KEY=" in lines:
            lines[lines.index("BAO_UNSEAL_KEY=")] = line
        else:
            lines.append(line)
        fd = os.open(".env", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"  BAO_UNSEAL_KEY — written (fingerprint {fingerprint(secret)}).  Next:  just bao-unseal")
        return
    if len(secret) != 16:
        sys.exit("refused: a password sheet has 12 words — that looks like the unseal-key sheet")
    phrase = " ".join(encode(secret))
    if path:
        _create(path, (phrase + "\n").encode())
        print(f"  {what} password → {path}  (fingerprint {fingerprint(phrase.encode())})")
        return
    try:
        live = backup_password(what.upper())
    except (OSError, subprocess.CalledProcessError):
        live = None
    if live is None:
        sys.exit(f"  sheet {fingerprint(phrase.encode())} — site/backup.env has no {what} password to compare it with")
    same = live == phrase
    print(f"  {'matches' if same else 'DOES NOT MATCH'} the {what} password (sheet {fingerprint(phrase.encode())}, box {fingerprint(live.encode())})")
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["sheet"] and len(a) == 2:
        cmd_sheet(a[1])
    elif a[:1] == ["phrase"] and len(a) == 2:
        cmd_phrase(a[1])
    elif a[:1] == ["words"] and len(a) in (2, 3):
        cmd_words(a[1], a[2] if len(a) == 3 else None)
    else:
        sys.exit(__doc__)
