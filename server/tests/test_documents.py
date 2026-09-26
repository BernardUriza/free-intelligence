"""Documents by reference (#50 item 6), offline: type detected, never trusted."""

import base64
import io

import pytest

from aire.engine import documents as d
from aire.engine.fetch import FetchRefused

def _pdf(pages: int = 1, password: str | None = None) -> bytes:
    from pypdf import PdfWriter
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    if password:
        writer.encrypt(password)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


PDF = _pdf()


def test_pdf_bytes_become_a_base64_pdf_block_with_its_title():
    block = d.to_block(PDF, 0, "acta.pdf")
    assert block == {"type": "document", "title": "acta.pdf",
                     "source": {"type": "base64", "media_type": "application/pdf",
                                "data": base64.b64encode(PDF).decode()}}


def test_text_bytes_become_a_text_block_even_if_the_caller_called_it_a_pdf():
    block = d.to_block("línea uno\nPERA 7719".encode(), 0, "falso.pdf")
    assert block["source"] == {"type": "text", "media_type": "text/plain", "data": "línea uno\nPERA 7719"}


def test_latin1_text_is_rescued():
    assert d.to_block("café".encode("latin-1"), 0)["source"]["data"] == "café"


@pytest.mark.parametrize("raw", [b"\x89PNG\r\n\x1a\n\x00\x00binary", b"x" * (d.MAX_TEXT_CHARS + 1)])
def test_binary_and_oversize_text_are_refused(raw):
    with pytest.raises(d.BadDocument):
        d.to_block(raw, 0)


@pytest.mark.parametrize("bad", ["x", [{}], [{"url": ""}], [{"url": "u"}] * (d.MAX_DOCUMENTS + 1)])
def test_the_shape_is_refused_before_any_fetch(bad):
    with pytest.raises(d.BadDocument):
        d.clean_documents(bad)


@pytest.mark.asyncio
async def test_a_refused_fetch_is_a_declared_error_naming_the_document(monkeypatch):
    async def fetch(url):
        if "evil" in url:
            raise FetchRefused("host not allowed: evil.com")
        return b"ok"
    monkeypatch.setattr(d, "fetch", fetch)
    with pytest.raises(d.BadDocument, match="document 1: host not allowed"):
        await d.prepare_documents([{"url": "https://cdn.discordapp.com/a.txt"}, {"url": "https://evil.com/x"}])


@pytest.mark.asyncio
async def test_prepare_fetches_and_types_each_in_order(monkeypatch):
    async def fetch(url):
        return PDF if url.endswith(".pdf") else b"notas"
    monkeypatch.setattr(d, "fetch", fetch)
    blocks = await d.prepare_documents([{"url": "https://c/a.pdf", "title": " acta "}, {"url": "https://c/n.txt"}])
    assert [b["source"]["type"] for b in blocks] == ["base64", "text"]
    assert blocks[0]["title"] == "acta" and "title" not in blocks[1]


def test_acp_carries_a_text_document_as_text_and_refuses_a_pdf():
    from aire.agent_sdk.acp_messages import _blocks
    text = d.to_block(b"PERA 7719", 0, "notas.txt")
    [block] = _blocks([text])
    assert "notas.txt" in str(block) and "PERA 7719" in str(block)
    with pytest.raises(ValueError, match="PDF"):
        _blocks([d.to_block(PDF, 0)])


@pytest.mark.asyncio
async def test_the_door_refuses_a_pdf_for_a_non_claude_provider_before_spending(monkeypatch):
    from fastapi import HTTPException

    from aire import intake

    async def docs(_raw):
        return (d.to_block(PDF, 0),)

    async def no_images(_raw):
        return ()
    async def empty_session(*_):
        return 0, 0
    monkeypatch.setattr(intake.attachment_budget, "held", empty_session)
    monkeypatch.setattr(intake, "prepare_documents", docs)
    monkeypatch.setattr(intake, "prepare_images", no_images)
    key = {"project_key": "pk", "session_id": "s"}
    with pytest.raises(HTTPException) as exc:
        await intake.safe_attachments(None, [{"url": "u"}], key, "codex")
    assert exc.value.status_code == 422 and "PDF" in exc.value.detail
    assert await intake.safe_attachments(None, [{"url": "u"}], key) == (d.to_block(PDF, 0),)


@pytest.mark.parametrize("raw,why", [
    (_pdf(d.MAX_PDF_PAGES + 1), "pages"),
    (_pdf(1, password="x"), "encrypted"),
    (b"%PDF-1.4\nnot really a pdf", "could not be read"),
])
def test_a_pdf_the_api_would_refuse_is_refused_here_before_spending(raw, why):
    with pytest.raises(d.BadDocument, match=why):
        d.to_block(raw, 0)


def test_a_pdf_at_the_page_cap_passes():
    assert d.to_block(_pdf(d.MAX_PDF_PAGES), 0)["source"]["media_type"] == "application/pdf"


def test_binary_that_is_not_utf8_and_has_no_nul_is_not_text():
    junk = bytes(range(0x80, 0x100)) * 50  # latin-1 decodes it, but it is not text
    with pytest.raises(d.BadDocument, match="neither a PDF nor text"):
        d.to_block(junk, 0)


@pytest.mark.asyncio
async def test_the_session_pdf_page_budget_counts_what_history_resends(monkeypatch):
    from aire.engine import attachment_budget as b

    held = [{"data": base64.b64encode(_pdf(60)).decode()}]

    async def rows(sql, *_):
        return held if sql is b._PDF_SQL else []
    monkeypatch.setattr(b, "_rows", rows)
    await b.check_pdf_pages("pk", "s", [base64.b64encode(_pdf(40)).decode()])
    with pytest.raises(b.OverBudget, match="100"):
        await b.check_pdf_pages("pk", "s", [base64.b64encode(_pdf(41)).decode()])
