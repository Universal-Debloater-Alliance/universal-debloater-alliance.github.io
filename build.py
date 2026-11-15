#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAV = [
    "Home",
    "Getting-started",
    "Usage",
    "FAQ",
    "Debloat-Lists",
    "UAD-CLI",
    "Building-from-source",
    "How-to-contribute",
    "Glossary",
    "ADB-Reference",
]
TITLES = {"FAQ": "FAQ", "UAD-CLI": "UAD CLI", "ADB-Reference": "ADB reference"}
ALERTS = {
    "note": "Note",
    "tip": "Tip",
    "important": "Important",
    "warning": "Warning",
    "caution": "Caution",
}
PUNCT = re.compile(r"[\u2000-\u206F\u2E00-\u2E7F\\'\"!#$%&()*+,./:;<=>?@\[\]^`{|}~]")
HEADING = re.compile(r"<h([1-6])>(.*?)</h\1>", re.DOTALL)
HREF = re.compile(r'\bhref="([^"]*)"')
TAGS = re.compile(r"<[^>]+>")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
QUOTE = re.compile(
    r"<blockquote>\s*<p>\[!(note|tip|important|warning|caution)\](?:\s*</p>)?\s*(.*?)</blockquote>",
    re.IGNORECASE | re.DOTALL,
)
CMARK = [
    "cmark-gfm",
    "--unsafe",
    "--github-pre-lang",
    "-e",
    "table",
    "-e",
    "strikethrough",
    "-e",
    "autolink",
    "-e",
    "tagfilter",
    "-e",
    "tasklist",
]


def slug(text: str) -> str:
    text = html.unescape(TAGS.sub("", text)).lower().strip()
    text = re.sub(r"\s", "-", PUNCT.sub("", text))
    return text or "section"


def title_of(stem: str) -> str:
    if stem in TITLES:
        return TITLES[stem]
    return " ".join(
        word if i == 0 or word.isupper() else word.lower() for i, word in enumerate(stem.split("-"))
    )


def page_of(stem: str) -> str:
    return "" if stem.lower() == "home" else stem.lower()


def link(src: str, dest: str) -> str:
    dest = html.unescape(dest).strip()
    if not dest or SCHEME.match(dest) or dest.startswith("//"):
        return dest
    if dest.startswith("/"):
        return "https://github.com" + dest
    if dest.startswith("#"):
        return "#" + slug(dest[1:])
    path, _, frag = dest.partition("#")
    path = path.strip().removeprefix("./").removesuffix(".md")
    dst = "" if path.lower() in ("", "home") else path.lower()
    frag = slug(frag) if frag else ""
    if src == dst:
        return f"#{frag}" if frag else "./"
    if not dst:
        base = "./" if not src else "../"
    else:
        base = f"{dst}/" if not src else f"../{dst}/"
    return f"{base}#{frag}" if frag else base


def cmark(markdown: str) -> str:
    result = subprocess.run(CMARK, input=markdown.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        sys.stderr.write(result.stderr.decode())
        sys.exit(f"cmark-gfm failed with status {result.returncode}")
    return result.stdout.decode()


def alerts(document: str) -> str:
    def replace(match: re.Match[str]) -> str:
        kind = match.group(1).lower()
        rest = match.group(2).strip()
        if rest.startswith("</p>"):
            rest = rest[4:].lstrip()
        else:
            rest = "<p>" + rest
        label = html.escape(ALERTS[kind])
        return f'<div class="alert alert-{kind}"><p class="alert-label">{label}</p>{rest}</div>'

    return QUOTE.sub(replace, document)


def heading_ids(document: str) -> str:
    seen: dict[str, int] = {}

    def replace(match: re.Match[str]) -> str:
        level, inner = match.group(1), match.group(2)
        base = slug(inner)
        n = seen.get(base, 0)
        seen[base] = n + 1
        ident = base if n == 0 else f"{base}-{n}"
        return f'<h{level} id="{ident}">{inner}</h{level}>'

    return HEADING.sub(replace, document)


def render(markdown: str, src: str) -> str:
    document = alerts(heading_ids(cmark(markdown)))
    return HREF.sub(lambda match: f'href="{html.escape(link(src, match.group(1)), quote=True)}"', document)


def fill(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace(f"@@{key}@@", value)
    return template


def nav(stems: list[str], src: str, current: str | None) -> str:
    items = []
    for stem in stems:
        slug = page_of(stem)
        mark = ' aria-current="page"' if slug == current else ""
        href = html.escape(link(src, slug or "Home"), quote=True)
        items.append(f'<a href="{href}"{mark}>{html.escape(title_of(stem))}</a>')
    return "\n".join(items)


def page(template: str, stems: list[str], slug: str, current: str | None, body: str, title: str) -> str:
    prefix = "" if slug == "" else "../"
    return fill(
        template,
        {
            "TITLE": html.escape(title),
            "CSS": f"{prefix}lupin.css",
            "LOGO": f"{prefix}logo.png",
            "HOME": "./" if slug == "" else "../",
            "NAV": nav(stems, slug, current),
            "CONTENT": body,
        },
    )


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: build.py WIKI OUT")
    wiki, out = Path(sys.argv[1]), Path(sys.argv[2])
    pages = {
        path.stem: path.read_text(encoding="utf-8")
        for path in wiki.glob("*.md")
        if not path.name.startswith("_")
    }
    if not pages:
        sys.exit(f"no markdown pages in {wiki}")
    rank = {stem: i for i, stem in enumerate(NAV)}
    stems = sorted(pages, key=lambda stem: (rank.get(stem, len(NAV)), stem.lower()))
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copyfile(ROOT / "assets" / "logo-dark.png", out / "logo.png")
    shutil.copyfile(ROOT / "lupin.css", out / "lupin.css")
    if (ROOT / "CNAME").is_file():
        shutil.copyfile(ROOT / "CNAME", out / "CNAME")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    for stem in stems:
        slug = page_of(stem)
        name = title_of(stem)
        body = render(pages[stem], slug)
        if "<h1" not in body:
            heading = "Universal Android Debloater Next Generation" if slug == "" else name
            body = f"<h1>{html.escape(heading)}</h1>\n{body}"
        title = "UAD-ng" if slug == "" else f"{name} — UAD-ng"
        dest = out / "index.html" if slug == "" else out / slug / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page(template, stems, slug, slug, body, title), encoding="utf-8")

    (out / "404.html").write_text(
        page(
            template,
            stems,
            "",
            None,
            "<h1>Page not found</h1>\n<p>This address is not in the UAD-ng wiki.</p>",
            "Page not found — UAD-ng",
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
