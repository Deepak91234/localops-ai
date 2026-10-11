import asyncio
import io
import json
from pathlib import Path
import socket
import zipfile

import httpx
import pytest

from app import knowledge_extract as extract


def document(tmp_path, name, content):
    path = tmp_path / name
    path.write_bytes(content.encode() if isinstance(content, str) else content)
    return path


def office(tmp_path, name, parts):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for key, value in parts.items():
            archive.writestr(key, value)
    return path


def test_text_encoding_and_binary_refusal(tmp_path):
    utf16 = document(tmp_path, "policy.txt", "Support hours: 09:00–17:00".encode("utf-16"))
    assert "09:00" in extract.extract_file(utf16, utf16.name)["text"]
    binary = document(tmp_path, "policy.txt", b"\xff\x80\x00garbage")
    result = extract.extract_file(binary, binary.name)
    assert result["status"] == "error" and not result["text"]


def test_unknown_empty_oversized_and_symlink(tmp_path):
    unknown = document(tmp_path, "model.bin", b"not a searchable document")
    assert extract.extract_file(unknown, unknown.name)["status"] == "stored"
    empty = document(tmp_path, "empty.txt", "")
    assert extract.extract_file(empty, empty.name)["status"] == "stored"
    large = tmp_path / "large.txt"
    with large.open("wb") as stream:
        stream.truncate(extract.MAX_FILE_BYTES + 1)
    assert "25 MB" in extract.extract_file(large, large.name)["error"]
    link = tmp_path / "link.txt"
    link.symlink_to(unknown)
    assert extract.extract_file(link, link.name)["status"] == "error"


def test_json_csv_html_and_text_limit(tmp_path):
    data = document(tmp_path, "data.json", '{"policy":"Review before sending"}')
    assert "Review before sending" in extract.extract_file(data, data.name)["text"]
    rows = document(tmp_path, "invoices.csv", "vendor,amount\nExample,100\nExample,250\n")
    result = extract.extract_file(rows, rows.name)
    assert result["metadata"]["columns"] == ["vendor", "amount"]
    assert result["metadata"]["row_count"] == 2
    page = document(tmp_path, "page.html", "<h1>Knowledge</h1><script>EVIL CODE</script><style>HIDDEN</style><p>A &amp; B</p>")
    text = extract.extract_file(page, page.name)["text"]
    assert "Knowledge" in text and "A & B" in text and "EVIL" not in text and "HIDDEN" not in text
    long = document(tmp_path, "long.txt", "a" * (extract.MAX_TEXT_CHARS + 20))
    result = extract.extract_file(long, long.name)
    assert len(result["text"]) == extract.MAX_TEXT_CHARS and result["metadata"]["truncated"]


def test_office_actual_xml_values_and_external_relationships_not_followed(tmp_path):
    docx = office(tmp_path, "policy.docx", {"word/document.xml": '<w:document xmlns:w="urn:word"><w:p><w:r><w:t>Vacation policy</w:t></w:r></w:p></w:document>', "word/_rels/document.xml.rels": '<Relationships><Relationship Target="http://127.0.0.1/private" TargetMode="External"/></Relationships>'})
    result = extract.extract_file(docx, docx.name)
    assert result["text"] == "Vacation policy"
    assert result["metadata"]["external_relationships_followed"] is False
    xlsx = office(tmp_path, "book.xlsx", {"xl/sharedStrings.xml": '<sst><si><t>Support</t></si></sst>', "xl/worksheets/sheet1.xml": '<worksheet><sheetData><row><c r="A1" t="s"><v>0</v></c><c r="B1"><v>250</v></c></row></sheetData></worksheet>'})
    text = extract.extract_file(xlsx, xlsx.name)["text"]
    assert "A1: Support" in text and "B1: 250" in text
    pptx = office(tmp_path, "slides.pptx", {"ppt/slides/slide1.xml": '<sld xmlns:a="urn:draw"><a:t>Local operations</a:t></sld>'})
    assert "Slide 1\nLocal operations" in extract.extract_file(pptx, pptx.name)["text"]


def test_archive_bomb_path_and_entity_are_refused(tmp_path):
    bomb = office(tmp_path, "bomb.docx", {"word/document.xml": "x" * 1_000_000})
    assert "compression" in extract.extract_file(bomb, bomb.name)["error"]
    traversal = office(tmp_path, "traversal.docx", {"../outside": "data", "word/document.xml": "<document/>"})
    assert "Unsafe" in extract.extract_file(traversal, traversal.name)["error"]
    entity = office(tmp_path, "entity.docx", {"word/document.xml": '<!DOCTYPE doc [<!ENTITY x "unsafe">]><doc>&x;</doc>'})
    assert "entity" in extract.extract_file(entity, entity.name)["error"]


def test_actual_local_image_ocr(tmp_path):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1300, 200), "white")
    ImageDraw.Draw(image).text((30, 55), "LOCALOPS SUPPORT HOURS 09:00", font=ImageFont.load_default(size=52), fill="black")
    path = tmp_path / "hours.png"
    image.save(path)
    result = extract.extract_file(path, path.name)
    assert result["status"] == "ready", result["error"]
    assert "LOCALOPS SUPPORT HOURS" in result["text"].upper()
    assert result["metadata"]["ocr"] and result["metadata"]["mean_confidence"] > 0.5


def test_scanned_pdf_uses_actual_local_ocr(tmp_path):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1000, 260), "white")
    ImageDraw.Draw(image).text((30, 75), "LOCAL SUPPORT POLICY", font=ImageFont.load_default(size=55), fill="black")
    path = tmp_path / "scan.pdf"
    image.save(path, "PDF")
    result = extract.extract_file(path, path.name)
    assert result["status"] == "ready", result["error"]
    assert "SUPPORT" in result["text"].upper() and "POLICY" in result["text"].upper() and result["metadata"]["ocr"]


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://user:password@example.com", "http://example.com:8080", "http://[fe80::1%25eth0]/", "http://example.com\\@localhost/", "http://example.com/\nsecret"])
def test_invalid_url_syntax_refused(url):
    with pytest.raises(ValueError):
        extract._validated_url(url)


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.0.1", "169.254.169.254", "0.0.0.0", "224.0.0.1", "::1", "fc00::1", "::ffff:127.0.0.1", "2002:7f00:1::"])
def test_nonpublic_ip_refused(address):
    assert not extract._public_ip(address)


async def test_mixed_dns_results_refused(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)), (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="non-public"):
        await extract._resolve_public("example.com", 443)


async def test_pinned_network_dials_literal_ip_without_second_dns_lookup():
    backend = extract._PinnedNetworkBackend("example.com", 443, ["93.184.216.34"])
    calls = []
    class Dialer:
        async def connect_tcp(self, host, port, *args):
            calls.append((host, port))
            return "approved connection"
    backend.backend = Dialer()
    assert await backend.connect_tcp("example.com", 443) == "approved connection"
    assert calls == [("93.184.216.34", 443)]
    with pytest.raises(Exception, match="outside"):
        await backend.connect_tcp("attacker.example", 443)


async def test_fetch_public_html_and_redirect_to_private_is_blocked(monkeypatch):
    connections = []
    def resolver(host, port, *args):
        address = "127.0.0.1" if host == "private.example" else "93.184.216.34"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]
    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    def response(request):
        connections.append(str(request.url))
        assert request.method == "GET" and "authorization" not in request.headers
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "http://private.example/private"}, stream=httpx.ByteStream(b""))
        return httpx.Response(200, headers={"content-type": "text/html"}, stream=httpx.ByteStream(b"<h1>Public handbook</h1><script>hidden</script>"))
    monkeypatch.setattr(extract, "_PinnedTransport", lambda *args: httpx.MockTransport(response))
    result = await extract.fetch_source("https://example.com/policy")
    assert result["status"] == "ready" and "Public handbook" in result["text"] and "hidden" not in result["text"]
    result = await extract.fetch_source("https://example.com/redirect")
    assert result["status"] == "error" and "non-public" in result["error"]
    assert all("private.example" not in url for url in connections)


async def test_fetch_size_compression_and_invalid_encoding_refused(monkeypatch):
    async def public(*args):
        return ["93.184.216.34"]
    monkeypatch.setattr(extract, "_resolve_public", public)
    for headers, body, expected in [({"content-length": str(extract.MAX_FETCH_BYTES + 1)}, b"", "5 MB"), ({"content-encoding": "gzip"}, b"compressed", "Compressed"), ({"content-type": "text/plain"}, b"\xff\xfe\xff", "decoding")]:
        monkeypatch.setattr(extract, "_PinnedTransport", lambda *args: httpx.MockTransport(lambda request: httpx.Response(200, headers=headers, stream=httpx.ByteStream(body))))
        result = await extract.fetch_source("https://example.com")
        assert result["status"] == "error" and expected in result["error"]


async def test_authenticated_api_get_redacts_reflection_and_refuses_every_redirect(monkeypatch):
    token = "local-test-secret-12345"
    async def public(*args):
        return ["93.184.216.34"]
    monkeypatch.setattr(extract, "_resolve_public", public)
    requests = []
    def response(request):
        requests.append(str(request.url))
        assert request.headers["authorization"] == "Bearer " + token
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "https://example.com/elsewhere"}, stream=httpx.ByteStream(b""))
        return httpx.Response(200, headers={"content-type": "application/json"}, stream=httpx.ByteStream(json.dumps({"policy": "Review before sending", "reflected": token}).encode()))
    monkeypatch.setattr(extract, "_PinnedTransport", lambda *args: httpx.MockTransport(response))
    result = await extract.fetch_source("https://example.com/api", {"Authorization": "Bearer " + token})
    assert result["status"] == "ready" and result["metadata"]["auth_configured"]
    assert token not in json.dumps(result) and "<redacted>" in result["text"]
    result = await extract.fetch_source("https://example.com/redirect", {"authorization": "Bearer " + token})
    assert result["status"] == "error" and "cannot follow redirects" in result["error"]
    assert len(requests) == 2 and token not in json.dumps(result)


async def test_authenticated_http_is_refused_before_dns_or_transport(monkeypatch):
    token = "transport-test-secret"
    async def unexpected(*args):
        raise AssertionError("Authenticated HTTP must be refused before DNS or transport")
    monkeypatch.setattr(extract, "_resolve_public", unexpected)
    monkeypatch.setattr(extract, "_PinnedTransport", unexpected)
    result = await extract.fetch_source("http://example.com/api", {"Authorization": "Bearer " + token})
    assert result["status"] == "error" and "require HTTPS" in result["error"]
    assert token not in json.dumps(result)


@pytest.mark.parametrize("headers", [{"Cookie": "secret"}, {"Authorization": "Basic secret"}, {"Authorization": "Bearer secret\r\nInjected: yes"}, {"Authorization": "Bearer " + "a" * 4097}, {"Authorization": "Bearer secret", "X-Key": "secret"}])
async def test_unsupported_auth_headers_are_not_sent(headers, monkeypatch):
    async def unexpected(*args):
        raise AssertionError("Invalid headers must be refused before DNS or HTTP")
    monkeypatch.setattr(extract, "_resolve_public", unexpected)
    result = await extract.fetch_source("https://example.com", headers)
    assert result["status"] == "error" and "secret" not in json.dumps(result)


async def test_fetch_stream_limit_without_content_length(monkeypatch):
    async def public(*args):
        return ["93.184.216.34"]
    monkeypatch.setattr(extract, "_resolve_public", public)
    monkeypatch.setattr(extract, "_PinnedTransport", lambda *args: httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "text/plain"}, stream=httpx.ByteStream(b"a" * (extract.MAX_FETCH_BYTES + 1)))))
    result = await extract.fetch_source("https://example.com")
    assert result["status"] == "error" and "5 MB" in result["error"]
