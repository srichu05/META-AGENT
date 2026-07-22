"""Validated, document-scoped storage for raw uploads."""

from pathlib import Path
from typing import Dict

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .exceptions import UploadValidationError
from .types import StoredUpload


class UploadStorage:
    """Stores accepted files beneath a document-specific configured root."""

    def __init__(self, upload_folder: str, supported_file_types: Dict[str, str], max_file_size_bytes: int):
        self.upload_folder = Path(upload_folder)
        self.supported_file_types = {extension.lower(): file_type for extension, file_type in supported_file_types.items()}
        self.max_file_size_bytes = max_file_size_bytes

    def detect_file_type(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        file_type = self.supported_file_types.get(extension)
        if not file_type:
            supported = ", ".join(sorted(self.supported_file_types))
            raise UploadValidationError(f"Unsupported file type. Supported extensions: {supported}")
        return file_type

    def save(self, file: FileStorage, document_id: str) -> StoredUpload:
        if not file or not file.filename:
            raise UploadValidationError("A file is required.")

        filename = secure_filename(file.filename)
        if not filename:
            raise UploadValidationError("The uploaded filename is invalid.")

        file_type = self.detect_file_type(filename)
        document_folder = self.upload_folder / document_id
        document_folder.mkdir(parents=True, exist_ok=True)
        storage_path = document_folder / filename
        file.save(str(storage_path))

        if storage_path.stat().st_size == 0:
            storage_path.unlink()
            raise UploadValidationError("The uploaded file is empty.")
        if storage_path.stat().st_size > self.max_file_size_bytes:
            storage_path.unlink()
            raise UploadValidationError("The uploaded file exceeds the configured size limit.")

        return StoredUpload(
            document_id=document_id,
            filename=filename,
            stored_filename=storage_path.name,
            file_type=file_type,
            storage_path=storage_path,
        )
