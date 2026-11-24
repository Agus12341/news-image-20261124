"""News Image 20261124 - a make.fun entry.

Ships a finished front-page image (entry.png) and writes it, byte for
byte, to the output directory after validating that it is a whole,
well-formed PNG within the competition's size caps.
"""

import os
import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1_048_576  # 1 MiB cap from the competition gate
MAX_WIDTH = 1024
MAX_HEIGHT = 1024

SOURCE_NAME = "entry.png"
OUTPUT_NAME = "entry.png"


def validate_png(data: bytes) -> tuple[int, int]:
    """Walk the PNG chunk stream, verifying every CRC.

    Returns (width, height) from the IHDR chunk. Raises ValueError on
    any structural problem: bad signature, truncated chunk, CRC
    mismatch, missing IHDR/IEND, or trailing garbage.
    """
    if len(data) > MAX_BYTES:
        raise ValueError(f"image is {len(data)} bytes, over the {MAX_BYTES} cap")
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("missing PNG signature")

    pos = len(PNG_SIGNATURE)
    width = height = None
    seen_iend = False
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError("truncated chunk header")
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        chunk_type = data[pos + 4:pos + 8]
        body_start = pos + 8
        body_end = body_start + length
        crc_end = body_end + 4
        if crc_end > len(data):
            raise ValueError(f"truncated {chunk_type!r} chunk")
        body = data[body_start:body_end]
        (stored_crc,) = struct.unpack(">I", data[body_end:crc_end])
        actual_crc = zlib.crc32(chunk_type + body) & 0xFFFFFFFF
        if actual_crc != stored_crc:
            raise ValueError(f"CRC mismatch in {chunk_type!r} chunk")
        if chunk_type == b"IHDR":
            if length != 13:
                raise ValueError("IHDR chunk must be 13 bytes")
            width, height = struct.unpack(">II", body[:8])
        elif chunk_type == b"IEND":
            seen_iend = True
            pos = crc_end
            break
        pos = crc_end

    if width is None:
        raise ValueError("no IHDR chunk found")
    if not seen_iend:
        raise ValueError("no IEND chunk found")
    if pos != len(data):
        raise ValueError("trailing bytes after IEND chunk")
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        raise ValueError(f"image is {width}x{height}, over the {MAX_WIDTH}x{MAX_HEIGHT} cap")
    return width, height


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.join(here, SOURCE_NAME)
    with open(source_path, "rb") as f:
        data = f.read()

    width, height = validate_png(data)

    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, OUTPUT_NAME)
    with open(output_path, "wb") as f:
        f.write(data)

    # Self-check: the bytes on disk must be exactly the validated source.
    with open(output_path, "rb") as f:
        written = f.read()
    assert written == data, "written bytes must equal the source image exactly"
    print(f"wrote {output_path}: {len(data)} bytes, {width}x{height} PNG, valid")


if __name__ == "__main__":
    main()
