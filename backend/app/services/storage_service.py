"""Lưu ảnh sự cố an toàn.

- Nhận diện loại ảnh bằng MAGIC BYTES (không tin Content-Type hay đuôi file người dùng gửi).
- Tên file do hệ thống sinh (uuid) nên không có path traversal / ghi đè file khác.
- Giới hạn dung lượng; chỉ nhận JPEG, PNG, WEBP.
"""
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import DomainError


def _detect_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_incident_image(upload: UploadFile) -> str:
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = upload.file.read(limit + 1)
    if not data:
        raise DomainError(422, "File ảnh rỗng")
    if len(data) > limit:
        raise DomainError(413, f"Ảnh vượt quá {settings.MAX_UPLOAD_MB} MB")
    ext = _detect_extension(data)
    if ext is None:
        raise DomainError(422, "Chỉ chấp nhận ảnh JPEG, PNG hoặc WEBP")
    folder = Path(settings.STORAGE_DIR) / "incidents"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (folder / name).write_bytes(data)
    return f"incidents/{name}"


def resolve(relative_path: str) -> Path:
    base = Path(settings.STORAGE_DIR).resolve()
    path = (base / relative_path).resolve()
    if base not in path.parents:  # chặn đường dẫn thoát khỏi thư mục storage
        raise DomainError(404, "Không tìm thấy ảnh")
    return path


def delete(relative_path: str | None) -> None:
    if relative_path:
        try:
            resolve(relative_path).unlink(missing_ok=True)
        except DomainError:
            pass
