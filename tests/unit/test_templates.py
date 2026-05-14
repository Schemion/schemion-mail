import re
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parsedate_to_datetime

from src.mail.templates import build_confirmation_card_message


def make_message(content: str = "Code: 123456") -> EmailMessage:
    message = EmailMessage()
    message["From"] = "no-reply@schemion.local"
    message["To"] = "user@example.com"
    message["Bcc"] = "hidden@example.com"
    message["Subject"] = "Registration confirmation"
    message.set_content(content)
    return message


def parse_message(raw_message: bytes) -> EmailMessage:
    return BytesParser(policy=policy.default).parsebytes(raw_message)


def test_build_confirmation_card_message_creates_plain_text_and_html_parts():
    result = parse_message(
        build_confirmation_card_message(make_message().as_bytes()),
    )

    assert result["From"] == "no-reply@schemion.local"
    assert result["To"] == "user@example.com"
    assert result["Subject"] == "Registration confirmation"
    assert result["Date"] is not None
    assert result["Message-ID"] is not None
    assert result["Bcc"] is None
    assert result.is_multipart()

    plain = result.get_body(preferencelist=("plain",))
    html = result.get_body(preferencelist=("html",))

    assert plain is not None
    assert html is not None
    assert "123456" in plain.get_content()
    assert "123456" in html.get_content()
    assert "Confirm your registration" in html.get_content()


def test_build_confirmation_card_message_uses_monochrome_palette():
    result = parse_message(
        build_confirmation_card_message(make_message().as_bytes()),
    )
    html = result.get_body(preferencelist=("html",)).get_content()
    colors = set(re.findall(r"#[0-9a-fA-F]{6}", html))

    assert colors <= {
        "#000000",
        "#ffffff",
        "#f2f2f2",
        "#d9d9d9",
        "#222222",
        "#cfcfcf",
        "#f7f7f7",
        "#555555",
    }


def test_build_confirmation_card_message_uses_placeholder_when_code_is_missing():
    result = parse_message(
        build_confirmation_card_message(make_message("Hello").as_bytes()),
    )
    html = result.get_body(preferencelist=("html",)).get_content()

    assert "------" in html


def test_build_confirmation_card_message_preserves_existing_delivery_headers():
    source = make_message()
    source["Date"] = "Thu, 14 May 2026 09:42:00 GMT"
    source["Message-ID"] = "<existing-message-id@schemion.local>"

    result = parse_message(
        build_confirmation_card_message(source.as_bytes()),
    )

    assert parsedate_to_datetime(result["Date"]) == parsedate_to_datetime("Thu, 14 May 2026 09:42:00 GMT")
    assert result["Message-ID"] == "<existing-message-id@schemion.local>"
