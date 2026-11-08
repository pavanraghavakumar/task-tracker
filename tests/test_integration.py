"""Cross-workstream contract checks for the integrated local application."""

from pathlib import Path


def test_frontend_proxy_and_http_methods_match_flask_routes():
    root = Path(__file__).parents[1]
    api_service = (root / "frontend/src/app/core/api.service.ts").read_text(encoding="utf-8")
    proxy = (root / "frontend/proxy.conf.json").read_text(encoding="utf-8")
    backend = (root / "backend/app.py").read_text(encoding="utf-8")

    assert "http.patch<ApiResponse<Task>>" in api_service
    assert "http.patch<ApiResponse<Category>>" in api_service
    assert '@app.patch("/api/v1/tasks/<int:task_id>")' in backend
    assert 'methods=["PATCH", "DELETE"]' in backend
    assert '"target": "http://127.0.0.1:5001"' in proxy


def test_backend_and_data_layer_share_critical_schema_contracts():
    root = Path(__file__).parents[1]
    backend_schema = (root / "backend/schema.sql").read_text(encoding="utf-8")
    data_schema = (root / "database/migrations/001_initial_schema.sql").read_text(encoding="utf-8")

    for contract in (
        "priority IN ('low', 'medium', 'high')",
        "status IN ('pending', 'in_progress', 'completed')",
        "REFERENCES categories(id) ON DELETE SET NULL",
    ):
        assert contract in backend_schema
        assert contract in data_schema
