from src.smtp.parser import (
    extract_smtp_path,
    is_data_terminator,
    parse_command,
    unescape_dot_stuffed_line,
)


def test_parse_command_uppercases_command_and_keeps_argument():
    command = parse_command("mail FROM:<sender@example.com>\r\n")

    assert command.name == "MAIL"
    assert command.arg == "FROM:<sender@example.com>"


def test_extract_smtp_path_supports_angle_brackets_and_plain_values():
    assert extract_smtp_path("FROM:<sender@example.com>", "FROM:") == "sender@example.com"
    assert extract_smtp_path("TO: user@example.com extra", "TO:") == "user@example.com"


def test_extract_smtp_path_rejects_missing_prefix_or_unclosed_bracket():
    assert extract_smtp_path("TO:<user@example.com>", "FROM:") is None
    assert extract_smtp_path("FROM:<sender@example.com", "FROM:") is None


def test_data_terminator_and_dot_stuffing_helpers():
    assert is_data_terminator(b".\r\n")
    assert is_data_terminator(b".\n")
    assert is_data_terminator(b".")
    assert not is_data_terminator(b"..\r\n")

    assert unescape_dot_stuffed_line(b"..hello\r\n") == b".hello\r\n"
    assert unescape_dot_stuffed_line(b"hello\r\n") == b"hello\r\n"
