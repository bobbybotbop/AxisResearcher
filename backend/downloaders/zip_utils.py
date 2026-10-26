import io
import zipfile

from backend.constants.files_3d import PREFERRED_3D_EXTENSIONS


def extract_best_3d_file(zip_bytes: bytes) -> tuple[str, bytes]:
    """
    Open a zip in memory and return (filename, file_bytes) for the best 3D file.

    Selection rules:
    - Extensions ranked by PREFERRED_3D_EXTENSIONS (index 0 = highest priority).
    - Among files with the same extension, the largest by uncompressed size wins.
    - Raises ValueError if no supported 3D file is found.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        infos = zf.infolist()

        candidates: dict[str, list[zipfile.ZipInfo]] = {
            ext: [] for ext in PREFERRED_3D_EXTENSIONS
        }
        for info in infos:
            if info.is_dir():
                continue
            if "." not in info.filename:
                continue
            ext = "." + info.filename.rsplit(".", 1)[-1].lower()
            if ext in candidates:
                candidates[ext].append(info)

        for ext in PREFERRED_3D_EXTENSIONS:
            matches = candidates[ext]
            if not matches:
                continue
            best = max(matches, key=lambda i: i.file_size)
            basename = best.filename.replace("\\", "/").rsplit("/", 1)[-1] or best.filename
            return basename, zf.read(best.filename)

    # no supported file found in zip
    supported = ", ".join(e.lstrip(".").upper() for e in PREFERRED_3D_EXTENSIONS)
    raise ValueError(f"No supported 3D file found in zip (supported: {supported})")
