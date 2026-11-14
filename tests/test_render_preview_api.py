import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import io

import pytest

from app import app

MINIMAL_STL = b"solid x\nendsolid x\n"


@pytest.fixture()
def client():
    return app.test_client()


@pytest.fixture(scope="module")
def box_3mf_bytes():
    import trimesh
    return trimesh.creation.box(extents=(10, 10, 10)).export(file_type="3mf")


@pytest.fixture(scope="module")
def box_step_bytes(tmp_path_factory):
    import gmsh
    path = tmp_path_factory.mktemp("meshes") / "box.step"
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("box")
        gmsh.model.occ.addBox(0, 0, 0, 10, 10, 10)
        gmsh.model.occ.synchronize()
        gmsh.write(str(path))
    finally:
        gmsh.finalize()
    return path.read_bytes()


def _post_preview(client, filename, data):
    return client.post(
        "/api/render-preview",
        data={"file": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


def _assert_stl_payload(data):
    import trimesh
    mesh = trimesh.load(io.BytesIO(data), file_type="stl")
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0


def test_preview_requires_a_file(client):
    res = client.post("/api/render-preview", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "file" in res.get_json()["error"].lower()


def test_preview_native_stl_returns_the_same_mesh(client):
    res = _post_preview(client, "model.stl", MINIMAL_STL)
    assert res.status_code == 200
    assert res.data == MINIMAL_STL


def test_preview_3mf_returns_converted_stl(client, box_3mf_bytes):
    res = _post_preview(client, "model.3mf", box_3mf_bytes)
    assert res.status_code == 200
    _assert_stl_payload(res.data)


def test_preview_step_returns_converted_stl(client, box_step_bytes):
    res = _post_preview(client, "model.step", box_step_bytes)
    assert res.status_code == 200
    _assert_stl_payload(res.data)


def test_preview_amf_is_rejected_with_friendly_error(client):
    res = _post_preview(client, "model.amf", b"<amf/>")
    assert res.status_code == 400
    assert "not supported" in res.get_json()["error"].lower()


def test_preview_corrupt_file_returns_friendly_error(client):
    res = _post_preview(client, "model.3mf", b"not a real archive")
    assert res.status_code == 400
    error = res.get_json()["error"]
    assert "Traceback" not in error
