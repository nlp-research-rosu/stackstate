"""Build site/index.html from src/page.template.html, src/fonts.css and site/data.json.

The page embeds a copy of data.json so it renders even if the live file can't be fetched;
it then rereads site/data.json every five minutes.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    tpl = (ROOT / "src" / "page.template.html").read_text(encoding="utf-8")
    fonts = (ROOT / "src" / "fonts.css").read_text(encoding="utf-8")
    data = (ROOT / "site" / "data.json").read_text(encoding="utf-8").replace("</", "<\\/")
    html = tpl.replace("__FONTS__", fonts).replace("__DATA__", data)
    (ROOT / "site" / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote site/index.html ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
