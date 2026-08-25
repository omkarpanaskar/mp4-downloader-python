import app as downloader


def test_homepage_renders():
    client = downloader.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"MP4" in response.data


def test_info_rejects_missing_url():
    client = downloader.app.test_client()

    response = client.post("/info", json={})

    assert response.status_code == 400
    assert response.get_json() == {"error": "No URL"}


def test_info_returns_formats(monkeypatch):
    expected = {
        "title": "Test video",
        "thumbnail": "https://example.com/thumb.jpg",
        "duration": 30,
        "formats": [{"format_id": "137", "label": "1080p"}],
    }
    monkeypatch.setattr(downloader, "fetch_formats", lambda url: expected)
    client = downloader.app.test_client()

    response = client.post("/info", json={"url": "https://example.com/video"})

    assert response.status_code == 200
    assert response.get_json() == expected


def test_download_rejects_missing_url():
    client = downloader.app.test_client()

    response = client.post("/download", json={"format_id": "137"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "No URL"}


def test_file_is_unavailable_before_download():
    client = downloader.app.test_client()

    response = client.get("/file/missing-job")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Not ready"}
