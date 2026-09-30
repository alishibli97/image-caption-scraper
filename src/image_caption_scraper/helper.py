"""Configuration and image download helpers."""

from __future__ import annotations

import base64
import io
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import requests
from PIL import Image

DEFAULT_HTTP_TIMEOUT = (5, 30)
DEFAULT_MAX_IMAGE_BYTES = 25 * 1024 * 1024


@dataclass
class ScraperConfig:
    engine: str = "all"
    num_images: int = 100
    query: str = "dog chases cat"
    out_dir: str | Path = "images"
    headless: bool = True
    driver: str | None = "chromedriver"
    expand: bool = False
    translate: bool = False
    k: int = 3
    min_width: int = 128
    min_height: int = 128
    queries: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        self.engine = self.engine.lower().strip()
        if self.engine not in {"all", "google", "yahoo", "flickr"}:
            raise ValueError("engine must be one of: all, google, yahoo, flickr")
        if not isinstance(self.num_images, int) or isinstance(self.num_images, bool):
            raise TypeError("num_images must be an integer")
        if self.num_images <= 0:
            raise ValueError("num_images must be greater than zero")
        if not isinstance(self.query, str) or not self.query.strip():
            raise ValueError("query must be a non-empty string")
        if not isinstance(self.k, int) or isinstance(self.k, bool) or self.k <= 0:
            raise ValueError("k must be a positive integer")
        if not isinstance(self.min_width, int) or self.min_width <= 0:
            raise ValueError("min_width must be a positive integer")
        if not isinstance(self.min_height, int) or self.min_height <= 0:
            raise ValueError("min_height must be a positive integer")

        self.query = self.query.strip()
        self.out_dir = Path(self.out_dir).expanduser()
        self.queries = {"English": self.query}


# Kept as an alias for code which imported the old internal helper.
parse_args = ScraperConfig


def _bounded_response_content(
    response: requests.Response,
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
) -> bytes:
    declared_size = response.headers.get("Content-Length")
    if declared_size and int(declared_size) > max_bytes:
        raise ValueError(f"image exceeds the {max_bytes}-byte download limit")

    content = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        content.extend(chunk)
        if len(content) > max_bytes:
            raise ValueError(f"image exceeds the {max_bytes}-byte download limit")
    return bytes(content)


def _decode_base64_image(url: str, max_bytes: int) -> bytes:
    try:
        _, encoded = url.split(",", 1)
    except ValueError as exc:
        raise ValueError("invalid data URL") from exc

    image_bytes = base64.b64decode(encoded, validate=True)
    if len(image_bytes) > max_bytes:
        raise ValueError(f"image exceeds the {max_bytes}-byte download limit")
    return image_bytes


def save_image(
    url: str,
    destination: str | Path,
    *,
    session: requests.Session | None = None,
    timeout: tuple[int, int] = DEFAULT_HTTP_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
    min_width: int = 1,
    min_height: int = 1,
    request_headers: Mapping[str, str] | None = None,
) -> Path:
    """Download or decode an image and save it as RGB JPEG."""

    if url.startswith(("http://", "https://")):
        requester = session or requests
        response = requester.get(
            url,
            headers=dict(request_headers or {}),
            stream=True,
            timeout=timeout,
        )
        response.raise_for_status()
        image_bytes = _bounded_response_content(response, max_bytes)
    elif url.startswith("data:"):
        image_bytes = _decode_base64_image(url, max_bytes)
    else:
        raise ValueError("image URL must use HTTP(S) or a base64 data URL")

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.load()
        if image.width < min_width or image.height < min_height:
            raise ValueError(
                f"image is too small ({image.width}x{image.height}); "
                f"minimum is {min_width}x{min_height}"
            )
        image.convert("RGB").save(target, "JPEG", quality=95)
    return target


def read_http(url: str, engine: str | Path, query: str | None = None, i: int | None = None) -> Path:
    """Backward-compatible wrapper around :func:`save_image`."""

    destination = Path(engine) if query is None else Path(engine) / query / f"{i}.jpg"
    return save_image(url, destination)


def read_base64(
    url: str, engine: str | Path, query: str | None = None, i: int | None = None
) -> Path:
    """Backward-compatible wrapper around :func:`save_image`."""

    destination = Path(engine) if query is None else Path(engine) / query / f"{i}.jpg"
    return save_image(url, destination)
