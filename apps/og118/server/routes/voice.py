"""Voice: text to speech and speech to text, each behind a per-account quota."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from fi_runner.auth import Principal
from deps import get_principal, get_stt_provider, get_tts_provider
from stt import (
    DEFAULT_UPLOAD_CONTENT_TYPE,
    MAX_AUDIO_BYTES,
    STTNotConfiguredError,
    STTProvider,
    STTUpstreamError,
    STTValidationError,
    safe_filename_for_mime,
    validate_audio,
    validate_mime,
)
from tts import (
    DEFAULT_FORMAT,
    TTSNotConfiguredError,
    TTSProvider,
    TTSUpstreamError,
    TTSValidationError,
    content_type_for,
    validate_request,
)
from voice_quota import verificar_cuota_de_voz

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None
    response_format: str = DEFAULT_FORMAT
    speed: float = 1.0


@router.post("/tts/synthesize")
async def tts_synthesize(
    req: TTSRequest,
    principal: Principal = Depends(get_principal),
    provider: TTSProvider | None = Depends(get_tts_provider),
) -> Response:
    """Synthesize speech for `text` and return the raw audio blob.

    This is the backend gate the frontend's `VoiceAdapter.synthesize` needs — it
    returns audio bytes + a Content-Type so the consumer can build an
    `AudioSource`. Gated by the same single-user bearer as /chat/stream.

    Failure is explicit and secret-free:
      - provider unconfigured (OG118_TTS_* unset) -> 503 TTS_NOT_CONFIGURED
      - bad input (empty/too-long text, bad format/speed) -> 400 TTS_INVALID_REQUEST
      - provider/network error -> 502 TTS_UPSTREAM_ERROR
    No request/response carries any secret value.
    """
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "TTS_NOT_CONFIGURED",
                "message": (
                    "TTS is not configured on this deployment. Set "
                    "OG118_TTS_ENDPOINT, OG118_TTS_API_KEY and OG118_TTS_DEPLOYMENT."
                ),
            },
        )

    # El upstream de voz se aprovisiona por RPM y es compartido con toda la
    # flota; sin este tope un solo llamante lo consume entero. Ver voice_quota.
    verificar_cuota_de_voz(principal.sub)

    try:
        validate_request(req.text, req.response_format, req.speed)
    except TTSValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "TTS_INVALID_REQUEST", "message": str(exc)},
        ) from None

    try:
        audio = await provider.synthesize(
            req.text,
            voice=req.voice or "",
            response_format=req.response_format,
            speed=req.speed,
        )
    except TTSNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "TTS_NOT_CONFIGURED", "message": str(exc)},
        ) from None
    except TTSUpstreamError as exc:
        # str(exc) is status-only / type-only by construction (see tts.py) — safe.
        raise HTTPException(
            status_code=502,
            detail={"code": "TTS_UPSTREAM_ERROR", "message": str(exc)},
        ) from None

    return Response(
        content=audio,
        media_type=content_type_for(req.response_format),
        headers={"Cache-Control": "private, max-age=0, no-store"},
    )


class TranscriptResponse(BaseModel):
    text: str


@router.post("/stt/transcribe")
async def stt_transcribe(
    audio: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
    provider: STTProvider | None = Depends(get_stt_provider),
) -> TranscriptResponse:
    """Transcribe one recorded audio chunk and return its text.

    This is the backend gate the frontend's `VoiceAdapter.transcribe` needs — it
    accepts a multipart audio upload and returns `{text}` so the consumer's
    `useDictation` can accumulate the transcript. Gated by the same single-user
    bearer as /chat/stream and /tts/synthesize.

    Failure is explicit and secret-free, mirroring /tts/synthesize:
      - provider unconfigured (OG118_STT_* unset) -> 503 STT_NOT_CONFIGURED
      - bad input (empty/too-large audio) -> 400 STT_INVALID_REQUEST
      - provider/network error -> 502 STT_UPSTREAM_ERROR
    No request/response carries any secret value.
    """
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "STT_NOT_CONFIGURED",
                "message": (
                    "STT is not configured on this deployment. Set "
                    "OG118_STT_ENDPOINT, OG118_STT_API_KEY and OG118_STT_DEPLOYMENT."
                ),
            },
        )

    # El upstream de voz se aprovisiona por RPM y es compartido con toda la
    # flota; sin este tope un solo llamante lo consume entero. Ver voice_quota.
    verificar_cuota_de_voz(principal.sub)

    # Cap the in-memory read at the audio limit + 1 (don't materialize an
    # arbitrarily large body before the size check ran post-read).
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "STT_AUDIO_TOO_LARGE",
                "message": f"audio exceeds the {MAX_AUDIO_BYTES // (1024 * 1024)} MB limit",
            },
        )
    content_type = audio.content_type or DEFAULT_UPLOAD_CONTENT_TYPE
    try:
        validate_audio(data)
        validate_mime(content_type)
    except STTValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "STT_INVALID_REQUEST", "message": str(exc)},
        ) from None

    try:
        text = await provider.transcribe(
            data,
            filename=safe_filename_for_mime(content_type),
            content_type=content_type,
        )
    except STTNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "STT_NOT_CONFIGURED", "message": str(exc)},
        ) from None
    except STTUpstreamError as exc:
        # str(exc) is status-only / type-only by construction (see stt.py) — safe.
        raise HTTPException(
            status_code=502,
            detail={"code": "STT_UPSTREAM_ERROR", "message": str(exc)},
        ) from None

    return TranscriptResponse(text=text)
