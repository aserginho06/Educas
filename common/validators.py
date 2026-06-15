from pathlib import Path

from django.core.exceptions import ValidationError


ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}
MAX_UPLOAD_SIZE = 50 * 1024 * 1024


def validate_upload_file(value):
    extension = Path(value.name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError("Tipo de arquivo nao permitido.")

    if value.size > MAX_UPLOAD_SIZE:
        raise ValidationError("Arquivo acima do limite de 50 MB.")
