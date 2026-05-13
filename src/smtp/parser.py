from dataclasses import dataclass


@dataclass(frozen=True)
class SMTPCommand:
    name: str
    arg: str


def parse_command(line: str) -> SMTPCommand:
    parts = line.strip("\r\n").split(" ", 1)

    name = parts[0].upper()
    arg = parts[1] if len(parts) > 1 else ""

    return SMTPCommand(
        name=name,
        arg=arg,
    )


def extract_smtp_path(arg: str, prefix: str) -> str | None:
    if not arg.upper().startswith(prefix):
        return None

    value = arg[len(prefix):].strip()

    if value.startswith("<"):
        end_index = value.find(">")

        if end_index == -1:
            return None

        return value[1:end_index].strip()

    if not value:
        return None

    return value.split()[0].strip()


def is_data_terminator(line: bytes) -> bool:
    return line in {b".\r\n", b".\n", b"."}


def unescape_dot_stuffed_line(line: bytes) -> bytes:
    if line.startswith(b".."):
        return line[1:]

    return line