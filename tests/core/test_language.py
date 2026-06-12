"""Tests for language cure — post-generation normalization."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from personas.insult.core.language import language_cure


@pytest.fixture
def mock_client():
    """Mock Anthropic client that returns cured text."""
    client = AsyncMock()
    return client


def _mock_response(text: str):
    """Create a mock API response with given text."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


class TestLanguageCure:
    @pytest.mark.asyncio
    async def test_translates_english_to_spanish(self, mock_client):
        mock_client.messages.create = AsyncMock(return_value=_mock_response("Pero Bernard, este video es INTENSO."))
        result = await language_cure(mock_client, "haiku", "But Bernard, this video is INTENSE.")
        assert result == "Pero Bernard, este video es INTENSO."

    @pytest.mark.asyncio
    async def test_returns_unchanged_spanish(self, mock_client):
        original = "¿En serio no sabes qué son las Corporate Wars?"
        mock_client.messages.create = AsyncMock(return_value=_mock_response(original))
        result = await language_cure(mock_client, "haiku", original)
        assert result == original

    @pytest.mark.asyncio
    async def test_preserves_react_markers(self, mock_client):
        cured = "Eso es un patrón clásico [REACT:💀]"
        mock_client.messages.create = AsyncMock(return_value=_mock_response(cured))
        result = await language_cure(mock_client, "haiku", "That's a classic pattern [REACT:💀]")
        assert "[REACT:💀]" in result

    @pytest.mark.asyncio
    async def test_strips_output_tags(self, mock_client):
        mock_client.messages.create = AsyncMock(return_value=_mock_response("<output>Texto curado aquí</output>"))
        result = await language_cure(mock_client, "haiku", "Cured text here in English")
        assert result == "Texto curado aquí"

    @pytest.mark.asyncio
    async def test_strips_response_wrapper(self, mock_client):
        # Regression v3.4.6: Haiku sometimes used <response> instead of <output>.
        mock_client.messages.create = AsyncMock(return_value=_mock_response("<response>Texto limpio</response>"))
        result = await language_cure(mock_client, "haiku", "Clean text in English")
        assert result == "Texto limpio"

    @pytest.mark.asyncio
    async def test_strips_input_wrapper(self, mock_client):
        # If Haiku echoes the input wrapper by mistake.
        mock_client.messages.create = AsyncMock(return_value=_mock_response("<input>Texto copiado</input>"))
        result = await language_cure(mock_client, "haiku", "Copied text in English")
        assert result == "Texto copiado"

    @pytest.mark.asyncio
    async def test_strips_leading_arrow_from_fewshot(self, mock_client):
        # The new prompt uses "→" to separate input/output in examples; Haiku
        # occasionally copies it as a prefix. Must be stripped.
        mock_client.messages.create = AsyncMock(return_value=_mock_response("→ Texto con flecha"))
        result = await language_cure(mock_client, "haiku", "Text with arrow in English")
        assert result == "Texto con flecha"
        assert not result.startswith("→")

    @pytest.mark.asyncio
    async def test_strips_wrapper_with_trailing_newline(self, mock_client):
        # Regression v3.4.7: v3.4.6 used startswith/endswith, which failed if
        # Haiku added a trailing \n. The scratchpad leak would come back.
        mock_client.messages.create = AsyncMock(return_value=_mock_response("<output>Texto curado</output>\n"))
        result = await language_cure(mock_client, "haiku", "Cured text in English")
        assert result == "Texto curado"
        assert "<" not in result

    @pytest.mark.asyncio
    async def test_strips_wrapper_with_leading_whitespace(self, mock_client):
        mock_client.messages.create = AsyncMock(return_value=_mock_response("  <output>Texto</output>"))
        result = await language_cure(mock_client, "haiku", "Text in English here")
        assert result == "Texto"

    @pytest.mark.asyncio
    async def test_strips_multiline_wrapped_content(self, mock_client):
        # Multiline payload inside wrapper — common for longer responses.
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response("<output>Línea uno.\n\nLínea dos.</output>")
        )
        result = await language_cure(mock_client, "haiku", "Line one.\n\nLine two here.")
        assert result == "Línea uno.\n\nLínea dos."

    @pytest.mark.asyncio
    async def test_returns_original_on_error(self, mock_client):
        mock_client.messages.create = AsyncMock(side_effect=Exception("API down"))
        original = "This should come back unchanged"
        result = await language_cure(mock_client, "haiku", original)
        assert result == original

    @pytest.mark.asyncio
    async def test_returns_original_on_empty_response(self, mock_client):
        mock_client.messages.create = AsyncMock(return_value=_mock_response(""))
        original = "Some mixed text here amigo"
        result = await language_cure(mock_client, "haiku", original)
        assert result == original

    @pytest.mark.asyncio
    async def test_returns_original_on_length_mismatch(self, mock_client):
        # Haiku returns something way too short
        mock_client.messages.create = AsyncMock(return_value=_mock_response("Si"))
        original = "This is a very long English sentence that should be translated properly"
        result = await language_cure(mock_client, "haiku", original)
        assert result == original

    @pytest.mark.asyncio
    async def test_skips_short_text(self, mock_client):
        result = await language_cure(mock_client, "haiku", "hola")
        assert result == "hola"
        mock_client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_empty_text(self, mock_client):
        result = await language_cure(mock_client, "haiku", "")
        assert result == ""

    @pytest.mark.asyncio
    async def test_sends_raw_text_without_xml_wrapper(self, mock_client):
        # Regression v3.4.6: user content must NOT be wrapped in <input> tags.
        # Doing so combined with XML few-shot taught Haiku to answer wrapped
        # in <output>...</output> and the tags sometimes leaked to users.
        mock_client.messages.create = AsyncMock(return_value=_mock_response("texto largo de prueba"))
        input_text = "some text here right now"
        await language_cure(mock_client, "haiku", input_text)
        call_args = mock_client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert user_msg == input_text
        assert "<input>" not in user_msg
        assert "</input>" not in user_msg
