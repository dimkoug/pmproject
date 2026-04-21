import io
import pytest
from httpx import AsyncClient


class TestFolders:
    async def test_create_folder(self, client: AsyncClient):
        r = await client.post("/api/dms/folders", json={"name": "Project Docs"})
        assert r.status_code == 201
        assert r.json()["name"] == "Project Docs"

    async def test_list_root_folders(self, client: AsyncClient):
        await client.post("/api/dms/folders", json={"name": "Folder A"})
        r = await client.get("/api/dms/folders")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_nested_folder(self, client: AsyncClient):
        parent = (await client.post("/api/dms/folders", json={"name": "Parent"})).json()
        child = (await client.post("/api/dms/folders", json={"name": "Child", "parent_id": parent["id"]})).json()
        r = await client.get(f"/api/dms/folders?parent_id={parent['id']}")
        assert r.status_code == 200
        names = [f["name"] for f in r.json()]
        assert "Child" in names

    async def test_delete_folder(self, client: AsyncClient):
        f = (await client.post("/api/dms/folders", json={"name": "Del Folder"})).json()
        r = await client.delete(f"/api/dms/folders/{f['id']}")
        assert r.status_code == 204


class TestDocuments:
    async def test_upload_document(self, client: AsyncClient):
        r = await client.post("/api/dms/documents",
            data={"title": "Test Doc", "tags": "test,sample"},
            files={"file": ("test.txt", b"Hello World", "text/plain")},
        )
        assert r.status_code == 201
        assert r.json()["title"] == "Test Doc"
        assert r.json()["version"] == 1

    async def test_list_documents(self, client: AsyncClient):
        await client.post("/api/dms/documents",
            data={"title": "List Doc"},
            files={"file": ("doc.txt", b"content", "text/plain")},
        )
        r = await client.get("/api/dms/documents")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_upload_new_version(self, client: AsyncClient):
        doc = (await client.post("/api/dms/documents",
            data={"title": "Versioned Doc"},
            files={"file": ("v1.txt", b"version 1", "text/plain")},
        )).json()
        r = await client.post(f"/api/dms/documents/{doc['id']}/versions",
            data={"change_notes": "Updated content"},
            files={"file": ("v2.txt", b"version 2", "text/plain")},
        )
        assert r.status_code == 201
        assert r.json()["version"] == 2

    async def test_list_versions(self, client: AsyncClient):
        doc = (await client.post("/api/dms/documents",
            data={"title": "Version List Doc"},
            files={"file": ("f.txt", b"data", "text/plain")},
        )).json()
        await client.post(f"/api/dms/documents/{doc['id']}/versions",
            data={}, files={"file": ("f2.txt", b"data2", "text/plain")},
        )
        r = await client.get(f"/api/dms/documents/{doc['id']}/versions")
        assert r.status_code == 200
        assert len(r.json()) == 2

    async def test_update_document_status(self, client: AsyncClient):
        doc = (await client.post("/api/dms/documents",
            data={"title": "Status Doc"},
            files={"file": ("s.txt", b"x", "text/plain")},
        )).json()
        r = await client.patch(f"/api/dms/documents/{doc['id']}?status=approved")
        assert r.status_code == 200
        assert r.json()["status"] == "approved"


class TestDocumentSearch:
    async def test_search(self, client: AsyncClient):
        await client.post("/api/dms/documents",
            data={"title": "Architecture Design", "tags": "architecture,design"},
            files={"file": ("arch.txt", b"content", "text/plain")},
        )
        r = await client.get("/api/dms/search?q=Architecture")
        assert r.status_code == 200
        assert any("Architecture" in d["title"] for d in r.json())

    async def test_search_by_tag(self, client: AsyncClient):
        await client.post("/api/dms/documents",
            data={"title": "Tagged Doc", "tags": "unique-tag-xyz"},
            files={"file": ("t.txt", b"x", "text/plain")},
        )
        r = await client.get("/api/dms/search?q=unique-tag-xyz")
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestDmsDashboard:
    async def test_dashboard(self, client: AsyncClient):
        r = await client.get("/api/dms/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "documents" in data
        assert "folders" in data
        assert "total_size_mb" in data
