"""Build the page from src/page.template.html, src/fonts.css, src/vendor/d3 and site/data.json.

Writes two files:
  site/index.html     a complete HTML document (for opening locally or hosting anywhere)
  dist/artifact.html  the same page without the document wrapper, for publishing as a claude.ai artifact

The page embeds a copy of data.json, so it renders even if the live file can't be fetched,
then rereads data.json every five minutes. d3 is bundled so charts draw without network access
(link previews are rendered without it).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    tpl = (ROOT / "src" / "page.template.html").read_text(encoding="utf-8")
    fonts = (ROOT / "src" / "fonts.css").read_text(encoding="utf-8")
    d3 = (ROOT / "src" / "vendor" / "d3.v7.9.0.min.js").read_text(encoding="utf-8")
    data = (ROOT / "site" / "data.json").read_text(encoding="utf-8").replace("</", "<\\/")
    page = tpl.replace("__D3__", d3).replace("__FONTS__", fonts).replace("__DATA__", data)
    (ROOT / "dist").mkdir(exist_ok=True)
    (ROOT / "dist" / "artifact.html").write_text(page, encoding="utf-8")
    (ROOT / "site" / "index.html").write_text('<!doctype html>\n<html lang="en">\n' + page + "</html>\n", encoding="utf-8")
    print(f"wrote site/index.html and dist/artifact.html ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
