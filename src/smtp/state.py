from dataclasses import dataclass, field


@dataclass
class SMTPSessionState:
    mail_from: str | None = None
    rcpt_tos: list[str] = field(default_factory=list)

    data_mode: bool = False
    data_chunks: list[bytes] = field(default_factory=list)
    data_size: int = 0
    data_too_large: bool = False

    def reset_transaction(self) -> None:
        self.mail_from = None
        self.rcpt_tos = []
        self.data_mode = False
        self.data_chunks = []
        self.data_size = 0
        self.data_too_large = False

    def start_data(self) -> None:
        self.data_mode = True
        self.data_chunks = []
        self.data_size = 0
        self.data_too_large = False