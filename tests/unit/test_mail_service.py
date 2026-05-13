from types import SimpleNamespace

from src.mail import service


def test_enqueue_incoming_smtp_message_formats_message_before_enqueue(monkeypatch):
    calls = {}

    def fake_build_confirmation_card_message(raw_message: bytes) -> bytes:
        calls["raw_message"] = raw_message
        return b"formatted-message"

    def fake_enqueue_mail(mail_from: str, rcpt_tos: list[str], raw_message: bytes) -> int:
        calls["mail_from"] = mail_from
        calls["rcpt_tos"] = rcpt_tos
        calls["enqueued_message"] = raw_message
        return 42

    monkeypatch.setattr(service, "build_confirmation_card_message", fake_build_confirmation_card_message)
    monkeypatch.setattr(service, "enqueue_mail", fake_enqueue_mail)

    email_id = service.enqueue_incoming_smtp_message(
        mail_from="sender@example.com",
        rcpt_tos=["user@example.com"],
        raw_message=b"Code: 123456",
    )

    assert email_id == 42
    assert calls == {
        "raw_message": b"Code: 123456",
        "mail_from": "sender@example.com",
        "rcpt_tos": ["user@example.com"],
        "enqueued_message": b"formatted-message",
    }


def test_process_delivery_result_marks_sent_after_success(monkeypatch):
    calls = []
    email = SimpleNamespace(id=7, attempts=1, max_attempts=5)
    result = SimpleNamespace(
        mx_host="mx.example.com",
        smtp_code=250,
        smtp_response="OK",
        success=True,
        temporary=False,
        error=None,
    )

    monkeypatch.setattr(service, "create_delivery_attempt", lambda **kwargs: calls.append(("attempt", kwargs)))
    monkeypatch.setattr(service, "mark_email_sent", lambda email_id: calls.append(("sent", email_id)))

    service.process_delivery_result(email, result)

    assert calls[0] == (
        "attempt",
        {
            "email_id": 7,
            "mx_host": "mx.example.com",
            "smtp_code": 250,
            "smtp_response": "OK",
            "success": True,
            "error": None,
        },
    )
    assert calls[1] == ("sent", 7)


def test_process_delivery_result_schedules_retry_for_temporary_failure(monkeypatch):
    calls = []
    email = SimpleNamespace(id=7, attempts=2, max_attempts=5)
    result = SimpleNamespace(
        mx_host="mx.example.com",
        smtp_code=451,
        smtp_response="Try later",
        success=False,
        temporary=True,
        error="Temporary error",
    )

    monkeypatch.setattr(service, "create_delivery_attempt", lambda **kwargs: calls.append(("attempt", kwargs)))
    monkeypatch.setattr(service, "calculate_next_attempt_at", lambda attempts: "next-at")
    monkeypatch.setattr(service, "mark_email_retry", lambda **kwargs: calls.append(("retry", kwargs)))

    service.process_delivery_result(email, result)

    assert calls[-1] == (
        "retry",
        {
            "email_id": 7,
            "error_message": "Temporary error",
            "next_attempt_at": "next-at",
        },
    )


def test_process_delivery_result_marks_failed_for_permanent_failure(monkeypatch):
    calls = []
    email = SimpleNamespace(id=7, attempts=5, max_attempts=5)
    result = SimpleNamespace(
        mx_host="mx.example.com",
        smtp_code=550,
        smtp_response="Rejected",
        success=False,
        temporary=False,
        error=None,
    )

    monkeypatch.setattr(service, "create_delivery_attempt", lambda **kwargs: calls.append(("attempt", kwargs)))
    monkeypatch.setattr(service, "mark_email_failed", lambda **kwargs: calls.append(("failed", kwargs)))

    service.process_delivery_result(email, result)

    assert calls[-1] == (
        "failed",
        {
            "email_id": 7,
            "error_message": "Unknown delivery error",
        },
    )
