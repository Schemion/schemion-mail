import asyncio
import logging

from src.core.config import settings
from src.mail.service import enqueue_incoming_smtp_message
from src.smtp.parser import extract_smtp_path, is_data_terminator, parse_command, unescape_dot_stuffed_line
from src.smtp.security import is_client_allowed
from src.smtp.state import SMTPSessionState


logger = logging.getLogger(__name__)


async def send_line(
    writer: asyncio.StreamWriter,
    line: str,
) -> None:
    writer.write((line + "\r\n").encode("utf-8"))
    await writer.drain()


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    peer = writer.get_extra_info("peername")
    peer_ip = peer[0] if peer else "unknown"

    logger.info("SMTP client connected: %s", peer_ip)

    if peer_ip == "unknown" or not is_client_allowed(peer_ip):
        await send_line(writer, "554 Relay access denied")
        writer.close()
        await writer.wait_closed()
        return

    state = SMTPSessionState()

    await send_line(
        writer,
        f"220 {settings.smtp_hostname} Simple SMTP Relay",
    )

    try:
        while True:
            raw_line = await reader.readline()

            if not raw_line:
                break

            if state.data_mode:
                await handle_data_line(
                    raw_line=raw_line,
                    state=state,
                    writer=writer,
                )
                continue

            text = raw_line.decode("utf-8", errors="replace").strip("\r\n")

            if not text:
                await send_line(writer, "500 Empty command")
                continue

            command = parse_command(text)

            if command.name in {"EHLO", "HELO"}:
                await send_line(writer, f"250-{settings.smtp_hostname}")
                await send_line(
                    writer,
                    f"250-SIZE {settings.smtp_max_message_bytes}",
                )
                await send_line(writer, "250 PIPELINING")

            elif command.name == "MAIL":
                mail_from = extract_smtp_path(command.arg, "FROM:")

                if not mail_from:
                    await send_line(writer, "501 Syntax: MAIL FROM:<address>")
                    continue

                state.mail_from = mail_from
                state.rcpt_tos = []

                await send_line(writer, "250 OK")

            elif command.name == "RCPT":
                rcpt_to = extract_smtp_path(command.arg, "TO:")

                if not state.mail_from:
                    await send_line(writer, "503 Need MAIL FROM first")
                    continue

                if not rcpt_to:
                    await send_line(writer, "501 Syntax: RCPT TO:<address>")
                    continue

                state.rcpt_tos.append(rcpt_to)

                await send_line(writer, "250 OK")

            elif command.name == "DATA":
                if not state.mail_from:
                    await send_line(writer, "503 Need MAIL FROM first")
                    continue

                if not state.rcpt_tos:
                    await send_line(writer, "503 Need RCPT TO first")
                    continue

                state.start_data()

                await send_line(
                    writer,
                    "354 End data with <CR><LF>.<CR><LF>",
                )

            elif command.name == "RSET":
                state.reset_transaction()
                await send_line(writer, "250 OK")

            elif command.name == "NOOP":
                await send_line(writer, "250 OK")

            elif command.name == "QUIT":
                await send_line(writer, "221 Bye")
                break

            elif command.name in {"AUTH", "STARTTLS"}:
                await send_line(
                    writer,
                    f"502 {command.name} not implemented",
                )

            else:
                await send_line(
                    writer,
                    f"502 Command not implemented: {command.name}",
                )

    except Exception:
        logger.exception("SMTP session failed for client %s", peer_ip)

    finally:
        logger.info("SMTP client disconnected: %s", peer_ip)

        writer.close()
        await writer.wait_closed()


async def handle_data_line(
    raw_line: bytes,
    state: SMTPSessionState,
    writer: asyncio.StreamWriter,
) -> None:
    if is_data_terminator(raw_line):
        await finish_data(
            state=state,
            writer=writer,
        )
        return

    raw_line = unescape_dot_stuffed_line(raw_line)

    state.data_size += len(raw_line)

    if state.data_size > settings.smtp_max_message_bytes:
        state.data_too_large = True
        return

    state.data_chunks.append(raw_line)


async def finish_data(
    state: SMTPSessionState,
    writer: asyncio.StreamWriter,
) -> None:
    state.data_mode = False

    if state.data_too_large:
        state.reset_transaction()
        await send_line(writer, "552 Message size exceeds fixed limit")
        return

    if not state.mail_from:
        state.reset_transaction()
        await send_line(writer, "503 Need MAIL FROM first")
        return

    if not state.rcpt_tos:
        state.reset_transaction()
        await send_line(writer, "503 Need RCPT TO first")
        return

    raw_message = b"".join(state.data_chunks)

    try:
        email_id = await asyncio.to_thread(
            enqueue_incoming_smtp_message,
            state.mail_from,
            state.rcpt_tos,
            raw_message,
        )

        logger.info(
            "Queued email id=%s from=%s to=%s size=%s",
            email_id,
            state.mail_from,
            state.rcpt_tos,
            len(raw_message),
        )

        await send_line(writer, f"250 Message queued as {email_id}")

    except Exception:
        logger.exception("Failed to enqueue email")
        await send_line(writer, "451 Requested action aborted: local error")

    finally:
        state.reset_transaction()