"""Build the page from src/page.template.html, src/fonts.css, src/vendor/d3 and site/data.json.

Writes two files:
  site/index.html     a complete HTML document (for opening locally or hosting anywhere)
  dist/artifact.html  the same page without the document wrapper, for publishing as a claude.ai artifact

The page embeds a copy of data.json, so it renders even if the live file can't be fetched,
then rereads data.json every five minutes. d3 is bundled so charts draw without network access
(link previews are rendered without it).
"""
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Public address of the hosted copy (Vercel). Link-preview cards need absolute URLs.
SITE_URL = os.environ.get("STACKSTATE_URL", "https://stackstate.ai").rstrip("/")
DESC = "Ship as fast as the machine can check. What unchecked code costs today, and how much of the world's software is verified. Updated daily."


def main():
    tpl = (ROOT / "src" / "page.template.html").read_text(encoding="utf-8")
    fonts = (ROOT / "src" / "fonts.css").read_text(encoding="utf-8")
    d3 = (ROOT / "src" / "vendor" / "d3.v7.9.0.min.js").read_text(encoding="utf-8")
    data = (ROOT / "site" / "data.json").read_text(encoding="utf-8").replace("</", "<\\/")
    page = tpl.replace("__D3__", d3).replace("__FONTS__", fonts).replace("__DATA__", data)
    (ROOT / "dist").mkdir(exist_ok=True)
    (ROOT / "dist" / "artifact.html").write_text(page, encoding="utf-8")
    social = "".join(
        f'<meta {a}="{k}" content="{v}">\n'
        for a, k, v in [
            ("property", "og:type", "website"),
            ("property", "og:title", "Stack State"),
            ("property", "og:description", DESC),
            ("property", "og:url", SITE_URL + "/"),
            ("property", "og:image", SITE_URL + "/og.png"),
            ("property", "og:image:width", "1200"),
            ("property", "og:image:height", "630"),
            ("name", "twitter:card", "summary_large_image"),
            ("name", "twitter:title", "Stack State"),
            ("name", "twitter:description", DESC),
            ("name", "twitter:image", SITE_URL + "/og.png"),
        ]
    )
    # Vercel Web Analytics (cookieless). The script is served by Vercel; elsewhere it is a harmless 404.
    analytics = '<script>window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };</script>\n<script defer src="/_vercel/insights/script.js"></script>\n'
    (ROOT / "site" / "index.html").write_text('<!doctype html>\n<html lang="en">\n' + page.replace("</title>\n", "</title>\n" + social + analytics, 1) + "</html>\n", encoding="utf-8")
    print(f"wrote site/index.html and dist/artifact.html ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
