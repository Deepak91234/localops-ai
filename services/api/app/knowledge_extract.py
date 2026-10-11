"""Bounded local document parsing and public, DNS-pinned, read-only URL imports.

Untrusted documents never execute code or follow Office external relationships.
Parsers run in a separate process; temporary files stay in the project directory.
"""
import asyncio
import codecs
import csv
import io
import ipaddress
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import socket
import ssl
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
import zipfile

import httpcore
import httpx
from httpcore._backends.auto import AutoBackend

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_FETCH_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_XML_BYTES = 10 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMP_ROOT = PROJECT_ROOT / "work" / "extraction-temp"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}


def _result(text="", mime_type="application/octet-stream", status="ready", error=None, metadata=None):
    info = dict(metadata or {})
    info["truncated"] = bool(info.get("truncated") or len(text) > MAX_TEXT_CHARS)
    text = text[:MAX_TEXT_CHARS].replace("\x00", "")
    if status == "ready" and not text.strip():
        status, error = "stored", error or "No readable text was found. The source cannot be searched until text is available."
    return {"text": text, "mime_type": mime_type, "status": status, "error": error, "metadata": info}


def _decode(raw, encoding=None):
    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        encoding = "utf-32"
    elif raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = "utf-16"
    elif raw.startswith(codecs.BOM_UTF8):
        encoding = "utf-8-sig"
    encoding = (encoding or "utf-8").lower()
    if encoding not in {"utf-8", "utf8", "utf-8-sig", "utf-16", "utf-32", "ascii", "iso-8859-1", "latin-1", "windows-1252", "cp1252"}:
        raise ValueError("Unsupported text encoding. Save the document as UTF-8 or Unicode with a byte-order mark.")
    try:
        text = raw.decode(encoding, errors="strict")
    except (UnicodeError, LookupError) as exc:
        raise ValueError("Text decoding failed. Save the document as UTF-8 or Unicode with a byte-order mark.") from exc
    if "\x00" in text or sum(ord(c) < 32 and c not in "\r\n\t" for c in text) > max(2, len(text) // 100):
        raise ValueError("The file contains binary control characters rather than supported readable text.")
    return text


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0
        self.characters = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self.hidden += 1
        elif not self.hidden and tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "section", "article"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden and self.characters <= MAX_TEXT_CHARS:
            self.parts.append(data)
            self.characters += len(data)


def _html_text(text):
    parser = _HTMLText()
    parser.feed(text)
    return re.sub(r"\n[ \t]*\n+", "\n\n", "".join(parser.parts)).strip()


def _xml(raw):
    if len(raw) > MAX_XML_BYTES:
        raise ValueError("An Office XML part exceeds the 10 MB parsing limit.")
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Office documents containing XML entity declarations are refused.")
    return ET.fromstring(raw)


def _safe_archive(path):
    archive = zipfile.ZipFile(path)
    try:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(entry.file_size for entry in entries) > MAX_ARCHIVE_BYTES:
            raise ValueError("Office archive exceeds the entry count or 50 MB expanded-size limit.")
        for entry in entries:
            name = PurePosixPath(entry.filename.replace("\\", "/"))
            if name.is_absolute() or ".." in name.parts or entry.flag_bits & 1:
                raise ValueError("Unsafe or encrypted Office archive entry refused.")
            if entry.file_size > MAX_XML_BYTES or entry.file_size > max(1, entry.compress_size) * 300:
                raise ValueError("Office archive exceeds per-entry size or compression-ratio limits.")
        return archive
    except Exception:
        archive.close()
        raise


def _office(path, suffix):
    with _safe_archive(path) as archive:
        names = archive.namelist()
        parts = []
        if suffix == ".docx":
            documents = [name for name in names if name == "word/document.xml" or re.fullmatch(r"word/(header|footer)\d+\.xml", name)]
            if "word/document.xml" not in documents:
                raise ValueError("This file is not a valid DOCX document.")
            for name in sorted(documents):
                root = _xml(archive.read(name))
                for paragraph in root.iter():
                    if paragraph.tag.rsplit("}", 1)[-1] == "p":
                        parts.append("".join(node.text or "" for node in paragraph.iter() if node.tag.rsplit("}", 1)[-1] == "t"))
        elif suffix == ".pptx":
            slides = sorted((name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)), key=lambda name: int(re.search(r"(\d+)\.xml", name)[1]))
            if not slides:
                raise ValueError("This file is not a valid PPTX presentation.")
            for index, name in enumerate(slides, 1):
                root = _xml(archive.read(name))
                parts.append(f"Slide {index}\n" + "\n".join(node.text or "" for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "t"))
        else:
            strings = []
            if "xl/sharedStrings.xml" in names:
                root = _xml(archive.read("xl/sharedStrings.xml"))
                strings = ["".join(n.text or "" for n in item.iter() if n.tag.rsplit("}", 1)[-1] == "t") for item in root if item.tag.rsplit("}", 1)[-1] == "si"]
            sheets = sorted(name for name in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
            if not sheets:
                raise ValueError("This file is not a valid XLSX workbook.")
            for index, name in enumerate(sheets, 1):
                parts.append(f"Sheet {index}")
                root = _xml(archive.read(name))
                for row in root.iter():
                    if row.tag.rsplit("}", 1)[-1] != "row":
                        continue
                    cells = []
                    for cell in row:
                        value = "".join(n.text or "" for n in cell.iter() if n.tag.rsplit("}", 1)[-1] in {"v", "t"})
                        if cell.get("t") == "s":
                            try:
                                value = strings[int(value)]
                            except (ValueError, IndexError):
                                raise ValueError("Invalid XLSX shared-string reference.") from None
                        cells.append(f"{cell.get('r', '')}: {value}")
                    parts.append(" | ".join(cells))
        return "\n".join(parts), {"extractor": "Office ZIP/XML", "external_relationships_followed": False, "note": "Document text and cached spreadsheet values only. Macros, formulas, external relationships, and embedded drawings are not executed."}


def _ocr(path):
    import warnings
    import numpy as np
    from PIL import Image, ImageOps
    from rapidocr_onnxruntime import RapidOCR
    Image.MAX_IMAGE_PIXELS = 25_000_000
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.width * image.height > 25_000_000:
                raise ValueError("Image exceeds the 25 million pixel OCR limit.")
            image = ImageOps.exif_transpose(image).convert("RGB")
            original = image.size
            image.thumbnail((2400, 2400))
            pixels = np.asarray(image)[:, :, ::-1].copy()
    engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
    lines, _ = engine(pixels)
    lines = lines or []
    text = "\n".join(str(line[1]) for line in lines)
    return text, {"extractor": "RapidOCR local CPU / ONNXRuntime", "ocr": True, "width": original[0], "height": original[1], "ocr_line_count": len(lines), "mean_confidence": round(sum(float(line[2]) for line in lines) / len(lines), 4) if lines else None, "ocr_note": "OCR can misread text; review the original before relying on figures."}


def _pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(path, strict=False)
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("Password-protected PDFs cannot be extracted without an unlocked copy.")
    page_count = len(reader.pages)
    if page_count > 250:
        raise ValueError("PDF exceeds the 250-page parsing limit.")
    parts, characters = [], 0
    for index, page in enumerate(reader.pages[:100], 1):
        text = page.extract_text() or ""
        parts.append(f"Page {index}\n{text}")
        characters += len(text)
        if characters > MAX_TEXT_CHARS:
            break
    metadata = {"extractor": "pypdf", "page_count": page_count, "pages_processed": len(parts), "truncated": len(parts) < page_count}
    # A scanned PDF requires real OCR, rather than indexing page labels as text.
    if not any(re.sub(r"\s", "", part.partition("\n")[2]) for part in parts):
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pdf-ocr-", dir=TEMP_ROOT) as directory:
            output = Path(directory) / "page"
            subprocess.run(["pdftoppm", "-f", "1", "-l", str(min(page_count, 5)), "-scale-to", "2000", "-png", str(path), str(output)], check=True, timeout=12, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            parts = []
            for index, image in enumerate(sorted(Path(directory).glob("page-*.png")), 1):
                text, _ = _ocr(image)
                if text.strip():
                    parts.append(f"Page {index}\n{text}")
            metadata.update(extractor="PDF rasterization + RapidOCR local CPU", ocr=True, pages_processed=min(page_count, 5), truncated=page_count > 5, ocr_note="Scanned PDFs process at most the first five pages. OCR may misread text.")
    return "\n\n".join(parts), metadata


def _extract_internal(path, filename):
    suffix = Path(filename).suffix.lower()
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    metadata = {"filename": Path(filename).name, "bytes": path.stat().st_size}
    if suffix in IMAGE_SUFFIXES:
        text, details = _ocr(path)
    elif suffix == ".pdf":
        text, details = _pdf(path)
    elif suffix in {".docx", ".xlsx", ".pptx"}:
        text, details = _office(path, suffix)
    elif suffix in {".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm", ".log", ".xml", ".yaml", ".yml"}:
        text = _decode(path.read_bytes())
        details = {"extractor": "local readable text"}
        if suffix in {".html", ".htm"}:
            text = _html_text(text)
        elif suffix == ".json":
            text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        elif suffix == ".csv":
            reader = csv.reader(io.StringIO(text))
            header = next(reader, [])
            rows, complete = 0, True
            for _ in reader:
                rows += 1
                if rows > 20_000:
                    complete = False
                    break
            details.update(columns=[value[:200] for value in header[:100]], row_count=rows, csv_complete=complete)
    else:
        return _result(mime_type=mime, status="stored", error="This format is stored but has no supported text extractor. Use PDF, Office, readable text, or a supported image.", metadata=metadata)
    return _result(text, mime, metadata={**metadata, **details})


def extract_file(path: Path, filename: str, *, timeout=40):
    """Return searchable text or an explicit stored/error result; never execute uploads."""
    path = Path(path)
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("The stored source must be a regular file, not a symbolic link.")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("File exceeds the 25 MB source limit.")
        if not path.stat().st_size:
            return _result(mime_type=mime, status="stored", error="The file is empty.")
        completed = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--extract", str(path.resolve()), Path(filename).name], capture_output=True, text=True, timeout=timeout, check=False, env={**os.environ, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2"})
        if completed.returncode != 0:
            raise ValueError("Document parser stopped at its resource limit or could not read the format.")
        return json.loads(completed.stdout)
    except subprocess.TimeoutExpired:
        return _result(mime_type=mime, status="error", error="Document extraction timed out; the original remains stored.")
    except Exception as exc:
        return _result(mime_type=mime, status="error", error=str(exc)[:400])


def _validated_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise ValueError("Enter a valid public HTTP or HTTPS URL, up to 2048 characters.")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("Only public HTTP/HTTPS URLs without embedded credentials are supported.")
    if "%" in parsed.hostname or "\\" in value:
        raise ValueError("Scoped addresses and ambiguous URL syntax are refused.")
    url = httpx.URL(value)
    port = url.port or (443 if url.scheme == "https" else 80)
    if port not in {80, 443}:
        raise ValueError("Public source URLs must use HTTP/HTTPS ports 80 or 443.")
    return url.copy_with(fragment=None), url.raw_host.decode("ascii"), port


def _public_ip(address):
    ip = ipaddress.ip_address(address)
    return ip.is_global and not ip.is_reserved and not ip.is_multicast and not (isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.sixtofour or ip.teredo))


async def _resolve_public(host, port):
    records = await asyncio.to_thread(socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(record[4][0] for record in records))
    if not addresses or not all(_public_ip(address) for address in addresses):
        raise ValueError("The URL resolves to a private, loopback, link-local, reserved, or otherwise non-public address.")
    return addresses


class _PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Only approved literal IPs reach connect_tcp; DNS is never consulted again."""
    def __init__(self, host, port, addresses):
        self.host, self.port, self.addresses = host, port, tuple(addresses)
        self.backend = AutoBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if host != self.host or port != self.port:
            raise httpcore.ConnectError("Connection outside the approved source origin was refused.")
        last_error = None
        for address in self.addresses:
            if not _public_ip(address):
                raise httpcore.ConnectError("Pinned address is not public.")
            try:
                return await self.backend.connect_tcp(address, port, timeout, local_address, socket_options)
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_error = exc
        raise last_error or httpcore.ConnectError("No approved public address was reachable.")

    async def connect_unix_socket(self, *args, **kwargs):
        raise httpcore.ConnectError("Unix sockets are not supported for public sources.")


class _PinnedTransport(httpx.AsyncHTTPTransport):
    def __init__(self, host, port, addresses):
        super().__init__(trust_env=False, retries=0)
        # HTTPX's pool adapter is pinned by requirements.lock. The origin host stays
        # unchanged for Host/SNI/certificate verification; only the dialed IP differs.
        self._pool = httpcore.AsyncConnectionPool(ssl_context=ssl.create_default_context(), network_backend=_PinnedNetworkBackend(host, port, addresses), max_connections=1, max_keepalive_connections=0, retries=0)


def _bearer_header(headers):
    if headers is None or headers == {}:
        return {}, None
    if not isinstance(headers, dict) or len(headers) != 1:
        raise ValueError("Only an optional Authorization Bearer header is supported.")
    name, value = next(iter(headers.items()))
    if not isinstance(name, str) or name.lower() != "authorization" or not isinstance(value, str):
        raise ValueError("Only an optional Authorization Bearer header is supported.")
    if not re.fullmatch(r"Bearer [!-~]{1,4096}", value):
        raise ValueError("The Bearer token must contain 1–4096 ASCII characters without whitespace or control characters.")
    return {"Authorization": value}, value[7:]


def _redact_result(result, token):
    def redact(value):
        if isinstance(value, str):
            return value.replace(token, "<redacted>") if token else value
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        return value
    result = {**result, "text": redact(result["text"]), "error": redact(result["error"]), "metadata": redact(result["metadata"])}
    if token and token in result["mime_type"]:
        result["mime_type"] = "application/octet-stream"
    result["text"] = result["text"][:MAX_TEXT_CHARS]
    result["metadata"]["auth_configured"] = bool(token)
    return result


async def fetch_source(url, headers: dict | None = None):
    """Fetch public source text once, revalidating and repinning every redirect."""
    token, safe_url = None, None
    try:
        authorization, token = _bearer_header(headers)
        async with asyncio.timeout(15):
            current = url
            for redirects in range(4):
                parsed, host, port = _validated_url(current)
                if authorization and parsed.scheme != "https":
                    raise ValueError("Authenticated API sources require HTTPS.")
                safe_url = safe_url or str(parsed)
                addresses = await _resolve_public(host, port)
                transport = _PinnedTransport(host, port, addresses)
                async with httpx.AsyncClient(transport=transport, trust_env=False, follow_redirects=False, timeout=httpx.Timeout(8, connect=5), headers={"User-Agent": "LocalOpsAI-SourceReader/1.0", "Accept": "text/html, text/plain, application/json, application/pdf;q=0.8, */*;q=0.1", "Accept-Encoding": "identity", **authorization}) as client:
                    async with client.stream("GET", parsed) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            if token:
                                raise ValueError("Authenticated sources cannot follow redirects. Use the final public URL directly.")
                            location = response.headers.get("location")
                            if not location:
                                raise ValueError("Source returned a redirect without a destination.")
                            current = urljoin(str(parsed), location)
                            continue
                        response.raise_for_status()
                        if response.headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
                            raise ValueError("Compressed source responses are refused to enforce the download-size limit.")
                        if int(response.headers.get("content-length", "0")) > MAX_FETCH_BYTES:
                            raise ValueError("Public source exceeds the 5 MB download limit.")
                        raw = bytearray()
                        async for part in response.aiter_raw():
                            if len(raw) + len(part) > MAX_FETCH_BYTES:
                                raise ValueError("Public source exceeds the 5 MB download limit.")
                            raw.extend(part)
                        mime = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0].strip().lower()
                        metadata = {"url": url, "final_url": str(parsed), "bytes": len(raw), "redirects": redirects, "fetched_at_origin": host, "fetch_method": "GET"}
                        if mime == "application/pdf" or bytes(raw[:5]) == b"%PDF-":
                            TEMP_ROOT.mkdir(parents=True, exist_ok=True)
                            with tempfile.TemporaryDirectory(prefix="url-", dir=TEMP_ROOT) as directory:
                                path = Path(directory) / "source.pdf"
                                path.write_bytes(raw)
                                result = await asyncio.to_thread(extract_file, path, "source.pdf", timeout=10)
                            result["metadata"].update(metadata)
                            return _redact_result(result, token)
                        if not (mime.startswith("text/") or mime in {"application/json", "application/xml", "application/xhtml+xml"}):
                            return _redact_result(_result(mime_type=mime, status="stored", error="This public URL has unsupported binary content. Upload the document to use its format-specific extractor.", metadata=metadata), token)
                        text = _decode(bytes(raw), response.encoding)
                        metadata["extractor"] = "public URL readable text"
                        if mime in {"text/html", "application/xhtml+xml"}:
                            text = _html_text(text)
                        elif mime == "application/json":
                            text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
                        return _redact_result(_result(text, mime, metadata=metadata), token)
            raise ValueError("Public source exceeded the three-redirect limit.")
    except TimeoutError:
        return _redact_result(_result(status="error", error="Public source fetch exceeded the 15 second time limit.", metadata={"url": safe_url} if safe_url else {}), token)
    except Exception as exc:
        return _redact_result(_result(status="error", error=str(exc)[:400], metadata={"url": safe_url} if safe_url else {}), token)


if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "--extract":
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_ARCHIVE_BYTES, MAX_ARCHIVE_BYTES))
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
        value = _extract_internal(Path(sys.argv[2]), sys.argv[3])
    except Exception as exc:
        value = _result(mime_type=mimetypes.guess_type(sys.argv[3])[0] or "application/octet-stream", status="error", error=str(exc)[:400])
    print(json.dumps(value, ensure_ascii=False))
