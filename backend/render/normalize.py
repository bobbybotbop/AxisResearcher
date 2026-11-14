"""Format normalization to the Render Mesh (GLOSSARY.md) before Blender sees it.

Native formats (.stl/.obj/.ply) pass through unconverted; .step/.stp are
converted to STL with the gmsh pip wheel, .3mf with trimesh (ADR 0001). The
converted STL is cached by content hash so a preview-then-render of the same
upload converts only once, and the same bytes back both the browser preview
and the Blender render.

Public seam: normalize_to_render_mesh().
"""

import hashlib
import os
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path

from backend.constants.render import (
    CONVERTIBLE_RENDER_EXTENSIONS,
    NATIVE_RENDER_EXTENSIONS,
    SUPPORTED_RENDER_EXTENSIONS,
)
from backend.render import RenderError, UnsupportedFormatError

# Bounded so long-running sessions don't fill the temp dir with stale meshes
_MESH_CACHE_MAX_ENTRIES = 20

_mesh_cache: "OrderedDict[str, str]" = OrderedDict()
_mesh_cache_lock = threading.Lock()


class ConversionError(RenderError):
    """A convertible upload could not be turned into an STL Render Mesh."""


def _convert_3mf_to_stl(src: str, dst: str) -> None:
    import trimesh

    loaded = trimesh.load(src)
    # Multi-part 3mf files load as a Scene; flatten to a single mesh
    if isinstance(loaded, trimesh.Scene):
        geometries = tuple(loaded.geometry.values())
        if not geometries:
            raise ConversionError("This .3mf file contains no geometry to render.")
        mesh = trimesh.util.concatenate(geometries)
    else:
        mesh = loaded
    mesh.export(dst)


def _convert_step_to_stl(src: str, dst: str) -> None:
    import gmsh

    # interruptible=False: renders run on a background thread, where gmsh's
    # default signal-handler install would fail
    gmsh.initialize(interruptible=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("render-mesh")
        shapes = gmsh.model.occ.importShapes(src)
        if not shapes:
            raise ConversionError("This STEP file contains no geometry to render.")
        gmsh.model.occ.synchronize()
        gmsh.model.mesh.generate(2)
        gmsh.write(dst)
    finally:
        gmsh.finalize()


# Lambdas resolve the module-level names at call time so tests can spy on them
_CONVERTERS = {
    ".3mf": lambda src, dst: _convert_3mf_to_stl(src, dst),
    ".step": lambda src, dst: _convert_step_to_stl(src, dst),
    ".stp": lambda src, dst: _convert_step_to_stl(src, dst),
}


def _validate_stl(path: str, display_name: str) -> None:
    import trimesh

    try:
        mesh = trimesh.load(path)
        valid = len(getattr(mesh, "vertices", [])) > 0
    except Exception:
        valid = False
    if not valid:
        raise ConversionError(
            f"'{display_name}' converted to an empty mesh. The file may be corrupt."
        )


def _cache_lookup(digest: str) -> Path | None:
    with _mesh_cache_lock:
        cached = _mesh_cache.get(digest)
        if cached is None:
            return None
        if not os.path.exists(cached):
            del _mesh_cache[digest]
            return None
        _mesh_cache.move_to_end(digest)
        return Path(cached)


def _cache_store(digest: str, path: str) -> None:
    with _mesh_cache_lock:
        _mesh_cache[digest] = path
        _mesh_cache.move_to_end(digest)
        while len(_mesh_cache) > _MESH_CACHE_MAX_ENTRIES:
            _, evicted = _mesh_cache.popitem(last=False)
            try:
                os.remove(evicted)
            except OSError:
                pass


def normalize_to_render_mesh(input_path) -> Path:
    """Return the path of the STL Render Mesh for an uploaded model file.

    Native formats return the input path unchanged; .step/.stp/.3mf are
    converted to a cached temp STL (repeat calls with identical bytes convert
    only once). Raises UnsupportedFormatError for formats that cannot be
    rendered at all (.amf, unknown) and ConversionError for corrupt or
    unconvertible files — both carry friendly, user-presentable messages.
    """
    input_path = Path(input_path)
    extension = input_path.suffix.lower()
    if extension in NATIVE_RENDER_EXTENSIONS:
        return input_path
    if extension not in CONVERTIBLE_RENDER_EXTENSIONS:
        raise UnsupportedFormatError(
            f"'{extension or input_path.name}' files are not supported for rendering. "
            f"Supported formats: {', '.join(SUPPORTED_RENDER_EXTENSIONS)}"
        )

    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    cached = _cache_lookup(digest)
    if cached is not None:
        return cached

    fd, output_path = tempfile.mkstemp(prefix="render_mesh_", suffix=".stl")
    os.close(fd)
    try:
        try:
            _CONVERTERS[extension](str(input_path), output_path)
        except RenderError:
            raise
        except Exception as e:
            raise ConversionError(
                f"Could not convert '{input_path.name}' ({extension}) to a renderable mesh: {e}"
            ) from e
        _validate_stl(output_path, input_path.name)
    except BaseException:
        try:
            os.remove(output_path)
        except OSError:
            pass
        raise

    _cache_store(digest, output_path)
    return Path(output_path)
