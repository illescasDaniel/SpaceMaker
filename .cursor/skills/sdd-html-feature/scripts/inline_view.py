#!/usr/bin/env python3
"""Derive the chat version of one tab of a feature page, or check the page's structure.

  inline_view.py PAGE.html TAB [--format html|md]
  inline_view.py --check PAGE.html [--legacy]

TAB: design, spec, arch, build, verify, appr (legacy pages also: qa, grade).
`verify` renders the Verify tab; a legacy page without it gets its QA and Grade tabs, each with its own glance.

html (default): status line, the tab's "At a glance" open, the detailed report in one <details class="big">, a source footer.
  When that is over HTML_LIMIT it emits the glance only, with a line telling the reader to open the page for the detailed report.
md: the same glance as Markdown for hosts that cannot render HTML, then the report anchor, then the gate line verbatim.
Both are extracted from the page, never retyped. Pass the output to the chat unedited.

--check: structural lint (exit 1 on errors, 0 with warnings only). --legacy, or a page with qa+grade
instead of verify, downgrades missing tabs and gate lines to warnings.
Elements to leave out of the chat copy: class "skip-inline" on a <p> or <nav>. Stdlib only.
"""
import re
import sys
from html import unescape
from html.parser import HTMLParser

HTML_LIMIT = 12000  # bytes; above this the detailed report is left out of the html copy (glance only); if even that is over, use --format md
TABS = ("design", "spec", "arch", "build", "verify", "appr", "qa", "grade")
STATUS = {"approved", "awaiting approval", "not started", "in progress", "blocked", "done", "n/a",
          "skipped", "unavailable", "pass", "needs work"}


def fail(msg: str) -> int:
    print("inline_view: " + msg, file=sys.stderr)
    return 1


def panel_body(html: str, tab: str) -> str:
    start = re.search(r'<div role="tabpanel" id="p-%s"[^>]*>' % re.escape(tab), html)
    if not start:
        raise ValueError("page has no panel p-%s" % tab)
    end = re.search(r'<div role="tabpanel"|</main>', html[start.end():])
    chunk = html[start.end(): start.end() + end.start()] if end else html[start.end():]
    chunk = re.sub(r'(?:\s*<!--(?:(?!-->).)*-->)*\s*$', "", chunk, flags=re.S)
    if not chunk.endswith("</div>"):
        raise ValueError("panel p-%s does not end with its closing </div>" % tab)
    body = chunk[: -len("</div>")]
    if len(re.findall(r"<div\b", body)) != len(re.findall(r"</div\s*>", body)):
        raise ValueError("panel p-%s has unbalanced <div> tags; refusing to emit a truncated copy" % tab)
    return body


def split_panel(body: str):
    body = re.sub(r"<(p|nav)\b[^>]*\bskip-inline\b[^>]*>.*?</\1>", "", body, flags=re.S)
    parts = re.split(r'<h2 class="rep">.*?</h2>', body, maxsplit=1, flags=re.S)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def chip_of(html: str, tab: str):
    """The status chip text of a tab's own button, or None when the button or its chip is missing."""
    button = re.search(r'<button\b[^>]*\bdata-p="%s"[^>]*>(.*?)</button>' % re.escape(tab), html, re.S)
    chip = re.search(r'<span class="st[^"]*">(.*?)</span>', button.group(1), re.S) if button else None
    return unescape(re.sub(r"<[^>]+>", "", chip.group(1))).strip() if chip else None


def status_of(html: str, tab: str) -> str:
    chip = chip_of(html, tab)
    return "unknown" if chip is None else chip


def badge_of(html: str) -> str:
    m = re.search(r'<span class="badge">(.*?)</span>', html, re.S)
    return unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


def panels_for(html: str, tab: str):
    """Tab name -> list of panel ids to render (verify falls back to qa+grade on legacy pages)."""
    if tab == "verify" and not re.search(r'id="p-verify"', html):
        return ["qa", "grade"]
    return [tab]


# ---------- Markdown ----------

class Md(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.gate, self.buf = [], [], None
        self.skip = None          # [tag, depth] while inside an omitted element
        self.in_gate = False
        self.table, self.row, self.cell, self.caption, self.cap_open = None, None, None, None, False
        self.list_depth, self.spans = 0, []

    def _emit(self, s):
        if self.cell is not None:
            self.cell.append(s)
        elif self.in_gate:
            self.gate.append(s)
        else:
            self.out.append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if self.skip:
            if tag == self.skip[0]:
                self.skip[1] += 1
            return
        if tag in ("svg", "style", "script") or (tag in ("p", "nav") and "skip-inline" in cls):
            self.skip = [tag, 1]
            return
        if tag == "p" and "gate" in cls:
            self.in_gate = True
            return
        if tag in ("h2", "h3"):
            self._emit("\n\n%s " % ("##" if tag == "h2" else "###"))
        elif tag == "p":
            self._emit("\n\n")
        elif tag in ("ul", "ol"):
            self.list_depth += 1
            self._emit("\n")
        elif tag == "li":
            self._emit("\n%s- " % ("  " * (self.list_depth - 1)))
        elif tag == "br":
            self._emit("  \n")
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")
        elif tag == "code":
            self._emit("`")
        elif tag == "summary":
            self._emit("\n\n**")
        elif tag == "span":
            self.spans.append("chip" in cls)
            if "chip" in cls:
                self._emit("[")
        elif tag == "table":
            self.table, self.caption = [], None
        elif tag == "caption":
            self.caption, self.cap_open = [], True
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("th", "td") and self.table is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[0]:
                self.skip[1] -= 1
                if self.skip[1] == 0:
                    self.skip = None
            return
        if tag == "p" and self.in_gate:
            self.in_gate = False
        elif tag in ("ul", "ol"):
            self.list_depth = max(0, self.list_depth - 1)
            self._emit("\n")
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")
        elif tag == "code":
            self._emit("`")
        elif tag == "summary":
            self._emit("**")
        elif tag == "span":
            if self.spans and self.spans.pop():
                self._emit("]")
        elif tag == "caption":
            self.cap_open = False
        elif tag in ("th", "td") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()).replace("|", "\\|"))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self._flush_table()

    def handle_data(self, data):
        if self.skip:
            return
        if self.cap_open:
            self.caption.append(data)
            return
        self._emit(data if self.cell is not None or self.in_gate else re.sub(r"\s+", " ", data))

    def _flush_table(self):
        rows = [r for r in self.table if r]
        if self.caption:
            self.out.append("\n\n**%s**" % " ".join("".join(self.caption).split()))
        if rows:
            width = max(len(r) for r in rows)
            rows = [r + [""] * (width - len(r)) for r in rows]
            self.out.append("\n\n| " + " | ".join(rows[0]) + " |\n|" + "---|" * width)
            for r in rows[1:]:
                self.out.append("\n| " + " | ".join(r) + " |")
        self.table = self.caption = None


def to_markdown(fragment: str):
    p = Md()
    p.feed(fragment)
    p.close()
    text = "\n".join(l.rstrip() for l in "".join(p.out).split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    gate = " ".join("".join(p.gate).split())
    return text, gate


# ---------- check ----------

# Tags that load a resource, and the attributes that carry its URL. <a href> is deliberately absent: a link loads nothing.
LOADING_TAGS = {"script", "img", "iframe", "frame", "source", "link", "video", "audio", "track", "embed",
                "object", "input", "form", "image", "use"}
URL_ATTRS = {"src", "href", "srcset", "data", "poster", "xlink:href", "action"}
TAG_RE = re.compile(r"<([a-zA-Z][\w:-]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*)>")
ATTR_RE = re.compile(r"""([^\s=/"'<>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?""")
REMOTE_URL = re.compile(r"\s*(?:(?:https?|ftp):)?//", re.I)
SRCSET_URL = re.compile(r"[\s,]*(\S+)")
SRCSET_DESCRIPTOR = re.compile(r"[^,]*")


def srcset_urls(value: str):
    """The candidate URLs of a srcset value (a data: URL may contain commas, so split like the HTML spec does)."""
    pos = 0
    while True:
        m = SRCSET_URL.match(value, pos)
        if not m:
            return
        pos, url = m.end(), m.group(1)
        if url.endswith(","):
            url = url.rstrip(",")
        else:
            pos = SRCSET_DESCRIPTOR.match(value, pos).end()
        yield url


def remote_assets(html: str):
    """(tag, attribute) pairs where a resource-loading tag points at an http, https, ftp or protocol-relative URL."""
    found = []
    for tm in TAG_RE.finditer(html):
        tag = tm.group(1).lower()
        if tag not in LOADING_TAGS:
            continue
        for am in ATTR_RE.finditer(tm.group(2)):
            name = am.group(1).lower()
            raw = next((g for g in am.groups()[1:] if g is not None), None)
            if name not in URL_ATTRS or raw is None:
                continue
            value = unescape(raw)
            urls = srcset_urls(value) if name == "srcset" else [value]
            if any(REMOTE_URL.match(u) for u in urls):
                found.append((tag, name))
    return found


def check(page: str, html: str, legacy: bool) -> int:
    errs, warns = [], []
    soft = warns if legacy else errs

    if '<style data-inline media="not all">' not in html:
        errs.append('missing <style data-inline media="not all"> block')
    buttons = re.findall(r'<button role="tab" id="t-([a-z]+)"[^>]*data-p="([a-z]+)"', html)
    panels = re.findall(r'<div role="tabpanel" id="p-([a-z]+)"', html)
    bt = {b for _, b in buttons}
    for b in sorted(bt - set(panels)):
        errs.append("tab %s has no panel p-%s" % (b, b))
    for p in sorted(set(panels) - bt):
        errs.append("panel p-%s has no tab button" % p)
    has_verify = "verify" in panels
    if not has_verify and "qa" in panels and "grade" in panels:
        legacy = True
        soft = warns
        warns.append("legacy page: QA and Grade tabs instead of Verify")
    required = ["design", "spec", "arch", "build", "appr"] + (["verify"] if has_verify or not legacy else [])
    for r in required:
        if r not in panels:
            soft.append("required tab %s is missing (add it with status n/a and a reason, never remove tabs)" % r)

    for m in re.finditer(r"<!--(.*?)-->", html, re.S):
        if "<div" in m.group(1) or "</main>" in m.group(1):
            errs.append("a comment contains <div or </main>; inline_view cannot extract panels safely")
    for tag, attr in remote_assets(html):
        errs.append("remote asset: <%s %s> loads from the network; inline it or remove it" % (tag, attr))
    if re.search(r"@import|url\(\s*['\"]?(?:(?:https?|ftp):)?//", html, re.I):
        errs.append("remote @import or url()")

    for t in panels:
        try:
            body = panel_body(html, t)
        except ValueError as exc:
            errs.append(str(exc))
            continue
        st = chip_of(html, t)
        label = (st or "").lower()
        if st is None:
            if t in bt:
                soft.append("tab %s: its tab button has no status chip (<span class=\"st ...\">)" % t)
        elif label not in STATUS and not re.fullmatch(r"\d+ of \d+ gates", label):
            soft.append("tab %s: status chip %r is not in the allowed vocabulary" % (t, st))
        if t != "appr":
            glance, detail = split_panel(body)
            if not re.search(r'<section id="[a-z]-glance"', glance):
                soft.append("tab %s: panel does not start with an At a glance section (id=x-glance)" % t)
            if len(re.findall(r'<h2 class="rep">', body)) != 1:
                soft.append("tab %s: needs exactly one <h2 class=\"rep\"> detailed report" % t)
            gates = re.findall(r'<p class="[^"]*\bgate\b[^"]*"', glance)
            if len(gates) != 1:
                soft.append("tab %s: needs exactly one <p class=\"note gate\"> in the glance (found %d)" % (t, len(gates)))
            if t == "design" and label != "n/a" and 'class="hero"' not in glance:
                warns.append("tab design: the At a glance has no hero visual (<div class=\"hero\">: a compact mock for frontend, the system diagram for backend; or N/A with a reason)")
            if re.search(r"<pre\b", glance):
                warns.append("tab %s: the At a glance contains <pre>; it renders as a code block in chat. Put verbatim agent lines in <li> or <p> items instead (keep <pre> for the detailed report)" % t)
            if re.search(r"\bQ\d+\.", detail) and 'class="questions"' not in glance:
                warns.append("tab %s: the report has open questions (Q1, ...) but the At a glance has no <details class=\"questions\"> with them" % t)
            n_svg = len(re.findall(r'<svg class="dg"', body))
            if n_svg > len(re.findall(r"Text equivalent", body)):
                soft.append("tab %s: a diagram has no 'Text equivalent' paragraph" % t)
            if label in ("approved", "done", "pass") and re.search(r'class="[^"]*\btpl\b', body):
                errs.append("tab %s is %s but still has template placeholders (class tpl)" % (t, st))
    if re.search(r"<script data-sample", html) and (chip_of(html, "design") or "").lower() in ("approved", "done"):
        errs.append("the template's <script data-sample> simulation is still in a page whose Design tab is approved or done")
    for w in warns:
        print("warning: " + w)
    for e in errs:
        print("error: " + e)
    print("%s: %d error(s), %d warning(s)" % (page, len(errs), len(warns)))
    return 1 if errs else 0


# ---------- main ----------

def main() -> int:
    argv = sys.argv[1:]
    sys.stdout.reconfigure(encoding="utf-8")
    fmt = "html"
    if "--format" in argv:
        i = argv.index("--format")
        fmt = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
        if fmt not in ("html", "md"):
            return fail("--format must be html or md")
    legacy = "--legacy" in argv
    argv = [a for a in argv if a != "--legacy"]
    do_check = "--check" in argv
    argv = [a for a in argv if a != "--check"]
    if (do_check and len(argv) != 1) or (not do_check and len(argv) != 2):
        print(__doc__, file=sys.stderr)
        return 2
    page = argv[0]
    try:
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
    except OSError as exc:
        return fail("cannot read %s: %s" % (page, exc.strerror))
    if do_check:
        return check(page, html, legacy)
    tab = argv[1]
    if tab not in TABS:
        return fail("unknown tab %s (use one of: %s)" % (tab, ", ".join(TABS)))
    style = re.search(r'<style data-inline media="not all">(.*?)</style>', html, re.S)
    if fmt == "html" and not style:
        return fail('page has no <style data-inline media="not all"> block')
    try:
        ids = panels_for(html, tab)
        splits = [(i, split_panel(panel_body(html, i))) for i in ids]
    except ValueError as exc:
        return fail(str(exc))

    badge = badge_of(html)
    if fmt == "html":
        def render(with_detail: bool) -> str:
            out = "<style>%s</style>\n" % style.group(1)
            for n, (i, (glance, detail)) in enumerate(splits):
                head = '<span class="badge">%s</span> ' % badge if n == 0 and badge else ""
                out += '<p class="hdr">%s<span class="chip def">%s tab: %s</span></p>\n%s\n' % (head, i, status_of(html, i), glance)
                if detail.strip():
                    if with_detail:
                        out += '<details class="big"><summary>Detailed report</summary>\n%s\n</details>\n' % detail
                    else:
                        out += '<p class="note">The detailed report is too large to show here. Open <code>%s#p-%s</code> in a browser to read it.</p>\n' % (page, i)
                out += '<p class="src">Source: %s#p-%s</p>\n' % (page, i)
            return out
        out = render(True)
        if len(out.encode("utf-8")) > HTML_LIMIT:
            full = len(out.encode("utf-8"))
            out = render(False)
            if len(out.encode("utf-8")) > HTML_LIMIT:
                print("inline_view: even the glance-only html is %d bytes (> %d); copying it into a renderer risks drift. Use --format md for chat." % (len(out.encode("utf-8")), HTML_LIMIT), file=sys.stderr)
            else:
                print("inline_view: full html was %d bytes (> %d); emitted the glance only, with a pointer to the page for the detailed report. Pass this output to the renderer as is." % (full, HTML_LIMIT), file=sys.stderr)
        sys.stdout.write(out)
        return 0
    chunks, gates = [], []
    for i, (glance, _detail) in splits:
        text, gate = to_markdown(glance)
        chunks.append("**%s tab: %s**\n\n%s\n\nDetailed report: %s#p-%s" % (i, status_of(html, i), text, page, i))
        if gate:
            gates.append(gate)
    head = ("**%s**\n\n" % badge) if badge else ""
    sys.stdout.write(head + "\n\n---\n\n".join(chunks) + ("\n\n" + "\n\n".join(gates) if gates else "") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
