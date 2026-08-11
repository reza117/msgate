"""EWS MIME attachment extraction (digest PDF)."""

from __future__ import annotations

from email import message_from_bytes
from email.message import EmailMessage

from exchangelib import FileAttachment, Mailbox, Message

from msgate.ews.client import mime_file_attachments
from msgate.ops.digest_pdf import text_pdf


def test_mime_file_attachments_finds_pdf() -> None:
    msg = EmailMessage()
    msg["Subject"] = "digest"
    msg.set_content("body text\n")
    pdf = text_pdf("title", ["line"])
    msg.add_attachment(pdf, maintype="application", subtype="pdf", filename="msgate-daily-digest.pdf")

    atts = mime_file_attachments(msg)
    assert len(atts) == 1
    assert atts[0].name == "msgate-daily-digest.pdf"
    assert atts[0].content.startswith(b"%PDF")


def test_exchangelib_message_accepts_file_attachment() -> None:
    """Sanity: FileAttachment can be attached before send_and_save."""
    ews_msg = Message(
        subject="digest",
        body="see pdf",
        to_recipients=[Mailbox(email_address="ops@example.com")],
    )
    ews_msg.attach(FileAttachment(name="report.pdf", content=text_pdf("t", ["a"])))
    assert len(ews_msg.attachments) == 1
    assert ews_msg.attachments[0].name == "report.pdf"


def test_plain_only_mime_has_no_attachments() -> None:
    raw = b"Subject: hi\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nhello\r\n"
    msg = message_from_bytes(raw)
    assert mime_file_attachments(msg) == []
