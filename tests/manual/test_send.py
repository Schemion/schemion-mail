import smtplib
from email.message import EmailMessage


msg = EmailMessage()

msg["From"] = "no-reply@schemion.local"
msg["To"] = "kelapep818@deapad.com"
msg["Subject"] = "Registration confirmation"

msg.set_content("Code: 123456")

with smtplib.SMTP("127.0.0.1", 1025, timeout=10) as smtp:
    smtp.send_message(msg)

print("Message sent to local SMTP")
