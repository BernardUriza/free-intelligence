"""The image-by-reference fetch (#50), offline: every SSRF guard has to be able
to go red. DNS is a fake resolver, the network is an httpx MockTransport."""

import httpx
import pytest

from aire.engine import fetch as f

URL = "https://cdn.discordapp.com/attachments/1/2/cat.png?ex=a&is=b&hm=c"


def _resolver(*answers):
    calls = []

    async def resolve(host):
        calls.append(host)
        return list(answers)
    resolve.calls = calls
    return resolve


def _transport(handler):
    seen = []

    def wrapped(request):
        seen.append(request)
        return handler(request)
    t = httpx.MockTransport(wrapped)
    t.seen = seen
    return t


@pytest.mark.asyncio
async def test_happy_path_connects_to_the_pinned_ip_keeping_host_and_sni():
    t = _transport(lambda r: httpx.Response(200, content=b"PNGBYTES"))
    assert await f.fetch(URL, resolve=_resolver("162.159.130.233"), transport=t) == b"PNGBYTES"
    req = t.seen[0]
    assert req.url.host == "162.159.130.233"
    assert req.headers["host"] == "cdn.discordapp.com"
    assert req.extensions["sni_hostname"] == "cdn.discordapp.com"
    assert req.url.query == b"ex=a&is=b&hm=c"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "https://evil.example.com/x.png",
    "http://cdn.discordapp.com/x.png",
    "https://cdn.discordapp.com:8443/x.png",
    "https://user@cdn.discordapp.com/x.png",
    "https://cdn.discordapp.com.evil.com/x.png",
])
async def test_off_allowlist_is_refused_before_any_dns(url):
    resolve = _resolver("162.159.130.233")
    with pytest.raises(f.FetchRefused):
        await f.fetch(url, resolve=resolve)
    assert resolve.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("answers", [
    ("127.0.0.1",), ("10.0.0.5",), ("169.254.169.254",), ("100.64.0.1",),
    ("::1",), ("fe80::1",), ("162.159.130.233", "192.168.1.1"), (),
])
async def test_rebinding_to_a_non_public_address_is_refused_without_connecting(answers):
    t = _transport(lambda r: httpx.Response(200, content=b"x"))
    with pytest.raises(f.FetchRefused):
        await f.fetch(URL, resolve=_resolver(*answers), transport=t)
    assert t.seen == []


@pytest.mark.asyncio
async def test_a_redirect_is_refused_not_followed():
    t = _transport(lambda r: httpx.Response(302, headers={"location": "http://169.254.169.254/"}))
    with pytest.raises(f.FetchRefused, match="redirect"):
        await f.fetch(URL, resolve=_resolver("162.159.130.233"), transport=t)
    assert len(t.seen) == 1


@pytest.mark.asyncio
async def test_an_expired_signature_is_a_declared_error():
    t = _transport(lambda r: httpx.Response(404))
    with pytest.raises(f.FetchRefused, match="404"):
        await f.fetch(URL, resolve=_resolver("162.159.130.233"), transport=t)


@pytest.mark.asyncio
async def test_oversize_is_refused_by_header_and_by_stream(monkeypatch):
    monkeypatch.setattr(f, "MAX_FETCH_BYTES", 10)
    declared = _transport(lambda r: httpx.Response(200, headers={"content-length": "999"}, content=b"x" * 999))
    streamed = _transport(lambda r: httpx.Response(200, stream=httpx.ByteStream(b"x" * 11)))
    for t in (declared, streamed):
        with pytest.raises(f.FetchRefused, match="too big"):
            await f.fetch(URL, resolve=_resolver("162.159.130.233"), transport=t)


@pytest.mark.asyncio
async def test_a_hang_is_cut_by_the_total_timeout(monkeypatch):
    import asyncio
    monkeypatch.setattr(f, "TOTAL_S", 0.05)

    async def slow(host):
        await asyncio.sleep(1)
        return ["162.159.130.233"]
    with pytest.raises(f.FetchRefused, match="timed out"):
        await f.fetch(URL, resolve=slow)
