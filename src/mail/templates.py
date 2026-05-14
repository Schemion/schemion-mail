import re
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import formatdate, make_msgid, parseaddr
from html import escape

from src.core.config import settings


CODE_PATTERN = re.compile(r"\b\d{4,8}\b")


def _get_text_content(message: Message) -> str:
    if message.is_multipart():
        body = message.get_body(preferencelist=("plain",))

        if body is None:
            return ""

        content = body.get_content()
        return content if isinstance(content, str) else ""

    content = message.get_content()
    return content if isinstance(content, str) else ""


def _extract_code(text: str) -> str:
    if match := CODE_PATTERN.search(text):
        return match.group(0)

    return "------"


def _message_id_domain(source: Message) -> str | None:
    for header in ("From", "Reply-To"):
        _, address = parseaddr(source.get(header, ""))
        if "@" not in address:
            continue

        domain = address.rsplit("@", 1)[1].strip().lower()
        if domain:
            return domain

    return settings.smtp_hostname or None


def build_confirmation_card_message(raw_message: bytes) -> bytes:
    source = BytesParser(policy=policy.default).parsebytes(raw_message)
    text_content = _get_text_content(source)
    code = _extract_code(text_content)

    message = EmailMessage(policy=policy.SMTP)

    for header in ("From", "To", "Cc", "Reply-To"):
        if value := source.get(header):
            message[header] = value

    message["Subject"] = source.get("Subject", "Registration confirmation")
    message["Date"] = source.get("Date", formatdate(localtime=False, usegmt=True))
    message["Message-ID"] = source.get("Message-ID", make_msgid(domain=_message_id_domain(source)))

    message.set_content(
        f"""Your confirmation code is {code}.

The code is valid for 10 minutes. If you did not request it, you can ignore this email.
"""
    )

    message.add_alternative(
        _render_confirmation_card_html(code=code),
        subtype="html",
    )

    return message.as_bytes(policy=policy.SMTP)


def _render_confirmation_card_html(code: str) -> str:
    escaped_code = escape(code)

    return f"""\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration confirmation</title>
  </head>
  <body style="margin:0;background:#f2f2f2;font-family:Arial,Helvetica,sans-serif;color:#000000;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f2f2f2;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#ffffff;border:1px solid #d9d9d9;border-radius:8px;overflow:hidden;">
            <tr>
              <td style="padding:28px 32px 22px;background:#000000;color:#ffffff;">
                <div style="font-size:13px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;">Schemion</div>
                <h1 style="margin:14px 0 0;font-size:24px;color:white;line-height:1.25;font-weight:700;">Confirm your registration</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <p style="margin:0 0 18px;font-size:16px;line-height:1.55;color:#222222;">
                  Use this code to finish creating your account.
                </p>
                <div style="margin:24px 0;padding:22px;border:1px solid #cfcfcf;border-radius:8px;background:#f7f7f7;text-align:center;">
                  <div style="font-size:12px;line-height:1.4;color:#555555;text-transform:uppercase;font-weight:700;letter-spacing:0.08em;">Confirmation code</div>
                  <div style="margin-top:12px;font-size:34px;line-height:1;font-weight:700;letter-spacing:0.18em;color:#000000;">{escaped_code}</div>
                </div>
                <p style="margin:0;font-size:14px;line-height:1.55;color:#555555;">
                  The code is valid for 10 minutes. If you did not request it, you can safely ignore this email.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px;background:#f7f7f7;border-top:1px solid #d9d9d9;color:#555555;font-size:12px;line-height:1.5;">
                This message was sent automatically by Schemion.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
