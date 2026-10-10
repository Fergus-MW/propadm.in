"""Agent email bodies are Markdown: send them as text plus safely rendered HTML."""

from markdown_it import MarkdownIt

# js-default disables raw HTML (no sanitiser needed) and keeps tables and strikethrough;
# breaks keeps single newlines, so greetings and signatures don't collapse into one line.
MARKDOWN = MarkdownIt("js-default", {"breaks": True})
CELL = 'style="border:1px solid #d0d0d0;padding:6px 10px;text-align:left"'


def email_html(markdown: str) -> str:
    html = MARKDOWN.render(markdown)
    # Email clients drop <style> blocks, so tables get inline borders.
    return (
        html.replace("<table>", '<table style="border-collapse:collapse">')
        .replace("<th>", f"<th {CELL}>")
        .replace("<td>", f"<td {CELL}>")
    )


if __name__ == "__main__":
    out = email_html("Hi **Jane**,\n\n| Item | £ |\n|---|---|\n| Boiler | 90 |\n\nThanks,\nProperly")
    assert "<strong>Jane</strong>" in out and "Thanks,<br" in out and "<td style=" in out
    assert "&lt;script&gt;" in email_html("<script>alert(1)</script>")
    assert 'href="javascript' not in email_html("[x](javascript:alert(1))")
    print("ok")
