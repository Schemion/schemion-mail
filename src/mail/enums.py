from enum import StrEnum


class MailStatus(StrEnum):
    QUEUED = "queued"
    SENDING = "sending"
    RETRY = "retry"
    SENT = "sent"
    FAILED = "failed"