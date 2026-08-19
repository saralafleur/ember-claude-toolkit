#!/usr/bin/env python3
"""
Render a finalized release-notes.md into a clean, self-contained client PDF,
with any images it references embedded inline.

Usage:
    python3 render_release_pdf.py <release-notes.md> [<output.pdf>] [--accent '#0b5fff']

If <output.pdf> is omitted, writes "<release-notes-dir>/release-notes.pdf".
--accent (optional) is a single hex color used for headings/rules/links --
the rest of the palette (paper, ink, borders) stays a fixed, neutral,
print-friendly default so this looks professional on any project without
per-project styling work. A project wanting its own full brand (fonts,
multi-color palette, decorative elements) should extend this script's CSS
rather than pile on more flags.

Requires: the `markdown` pip package (`pip install markdown`), and a local
Chrome/Chromium install (same requirement release-quicksheets already
carries for this project, if configured -- this script doesn't depend on
that skill, it just reuses the same headless-Chrome-print-to-pdf technique
so this family of tools has one recipe, not two).

Self-contained output: every local image the markdown references (relative
paths resolved against the markdown file's own directory) is base64-embedded
into the HTML before printing, so the PDF has no external references and
renders identically regardless of where it's later opened.
"""
import base64
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import markdown as _markdown
except ImportError:
    sys.exit(
        "The 'markdown' pip package is required (pip install markdown). "
        "It was expected to already be available; if this environment "
        "genuinely lacks it, install it before re-running."
    )

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]

CSS_TEMPLATE = """
:root {
  --paper: #ffffff;
  --ink: #1a2433;
  --ink-soft: #55677d;
  --line: #dde3ea;
  --accent: ACCENT_COLOR;
  --font-display: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
  --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font-family: var(--font-body); font-size: 11pt; line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
.doc { max-width: 720px; margin: 0 auto; padding: 2.4rem 1.75rem 3rem; }
h1 {
  font-family: var(--font-display); font-weight: 700; font-size: 1.9rem;
  color: var(--ink); margin: 0 0 0.3rem; letter-spacing: -0.01em;
}
h1 + p { color: var(--ink-soft); font-size: 0.95rem; margin-top: 0; }
h2 {
  font-family: var(--font-display); font-weight: 700; font-size: 1.25rem;
  color: var(--accent); margin: 2.2rem 0 0.9rem; padding-bottom: 0.4rem;
  border-bottom: 2px solid var(--accent); page-break-after: avoid;
}
h3 {
  font-family: var(--font-display); font-weight: 600; font-size: 1.05rem;
  color: var(--ink); margin: 1.4rem 0 0.5rem; page-break-after: avoid;
}
p { margin: 0 0 0.85rem; }
ul, ol { margin: 0 0 1rem; padding-left: 1.4rem; }
li { margin-bottom: 0.45rem; }
li > p { margin-bottom: 0.3rem; }
strong { color: var(--ink); }
hr {
  border: none; border-top: 1px solid var(--line); margin: 1.8rem 0;
}
figure {
  margin: 1.1rem 0 1.6rem; padding: 0; page-break-inside: avoid;
  break-inside: avoid; display: flex; flex-direction: column; align-items: center;
}
figure img {
  display: block; width: auto; height: auto;
  max-width: 100%; max-height: 9.2in; /* fit within one printed page */
  border: 1px solid var(--line); border-radius: 8px;
  box-shadow: 0 1px 2px rgba(20,30,45,0.06), 0 8px 20px -12px rgba(20,30,45,0.18);
}
figcaption {
  margin-top: 0.5rem; font-size: 0.82rem; color: var(--ink-soft);
  text-align: center; font-style: italic;
}
blockquote {
  margin: 0 0 1rem; padding: 0.15rem 0 0.15rem 1rem;
  border-left: 3px solid var(--accent); color: var(--ink-soft);
}
code {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.88em; background: #f2f4f7; padding: 0.1em 0.35em; border-radius: 4px;
}
a { color: var(--accent); text-decoration: none; }
table { border-collapse: collapse; width: 100%; margin: 0 0 1.2rem; font-size: 0.92rem; }
th, td { border: 1px solid var(--line); padding: 0.45rem 0.6rem; text-align: left; }
th { background: #f7f9fb; font-weight: 600; }
@media print {
  .doc { padding: 0; }
  figure { page-break-before: always; page-break-inside: avoid; }
}
"""


def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    sys.exit("No Chrome/Chromium install found in the expected locations.")


def b64_image(path):
    data = path.read_bytes()
    ext = path.suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"data:image/{mime};base64,{base64.b64encode(data).decode('ascii')}"


def embed_local_images(md_text, md_dir):
    """Replace ![alt](relative/path.png) with a base64 data: URI, wrapped in
    a <figure> with the alt text as a caption -- Python-Markdown passes
    plain <img> tags through untouched, so do this as a pre-pass on the
    raw markdown rather than post-processing HTML."""

    def _replace(match):
        alt, rel_path = match.group(1), match.group(2)
        if rel_path.startswith(("http://", "https://", "data:")):
            return match.group(0)  # leave remote/data URIs alone
        img_path = (md_dir / rel_path).resolve()
        if not img_path.exists():
            print(f"WARNING: referenced image not found, leaving as-is: {rel_path}", file=sys.stderr)
            return match.group(0)
        data_uri = b64_image(img_path)
        caption = f"<figcaption>{alt}</figcaption>" if alt else ""
        return f'<figure><img src="{data_uri}" alt="{alt}">{caption}</figure>'

    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _replace, md_text)


def render_pdf(md_path, out_path, accent):
    md_path = Path(md_path).resolve()
    md_text = md_path.read_text()
    md_text = embed_local_images(md_text, md_path.parent)

    body_html = _markdown.markdown(
        md_text, extensions=["extra", "sane_lists"]
    )
    css = CSS_TEMPLATE.replace("ACCENT_COLOR", accent)
    html = f"""<!DOCTYPE html>
<html data-theme="light">
<head><meta charset="utf-8"><style>{css}</style></head>
<body><div class="doc">{body_html}</div></body>
</html>"""

    chrome = find_chrome()
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
        html_path = f.name

    out_path = Path(out_path).resolve()
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox",
         f"--print-to-pdf={out_path}", "--no-pdf-header-footer",
         f"file://{html_path}"],
        check=True, capture_output=True,
    )
    Path(html_path).unlink(missing_ok=True)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    raw = sys.argv[1:]
    if not raw:
        sys.exit(__doc__)

    accent = "#0b5fff"
    positional = []
    i = 0
    while i < len(raw):
        tok = raw[i]
        if tok == "--accent":
            accent = raw[i + 1]
            i += 2
        elif tok.startswith("--accent="):
            accent = tok.split("=", 1)[1]
            i += 1
        else:
            positional.append(tok)
            i += 1

    if not positional:
        sys.exit(__doc__)
    md_arg = Path(positional[0])
    out_arg = positional[1] if len(positional) > 1 else md_arg.with_name("release-notes.pdf")
    render_pdf(md_arg, out_arg, accent)
