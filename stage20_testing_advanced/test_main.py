import pytest
from sqlalchemy import func, select

from app.models import Task
from app.services import TaskPolicy, get_policy

pytestmark = pytest.mark.integration


def test_create_persists_to_test_database(client, db_session):
    response = client.post("/tasks", json={"title": "Learn fixtures"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "title": "Learn fixtures", "completed": False}
    task = db_session.get(Task, 1)
    assert task is not None and task.title == "Learn fixtures"


def test_full_crud_workflow(client, db_session):
    created = client.post("/tasks", json={"title": "Practice CRUD"}).json()
    path = f'/tasks/{created["id"]}'
    assert client.get(path).json() == created
    assert client.patch(path, json={"completed": True}).json()["completed"] is True
    assert client.get(path).json()["completed"] is True
    response = client.delete(path)
    assert response.status_code == 204 and response.content == b""
    assert client.get(path).status_code == 404
    assert db_session.scalar(select(func.count()).select_from(Task)) == 0


@pytest.mark.parametrize("title", ["", "   ", "a" * 81, None, 123])
def test_invalid_title_does_not_write(client, db_session, title):
    assert client.post("/tasks", json={"title": title}).status_code == 422
    assert db_session.scalar(select(func.count()).select_from(Task)) == 0


@pytest.mark.parametrize("title", ["a", "a" * 80, "中文任务"])
def test_valid_title_boundaries(client, title):
    assert client.post("/tasks", json={"title": title}).json()["title"] == title


def test_title_normalized_and_duplicate_rejected(client):
    assert client.post("/tasks", json={"title": "  same  "}).status_code == 201
    response = client.post("/tasks", json={"title": "same"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Task title already exists"}
    assert client.post("/tasks", json={"title": "different"}).status_code == 201


def test_task_factory_is_visible_to_request_session(client, task_factory):
    first = task_factory(title="seeded")
    second = task_factory(completed=True)
    assert client.get(f"/tasks/{first.id}").json()["title"] == "seeded"
    assert client.get(f"/tasks/{second.id}").json()["completed"] is True


@pytest.mark.parametrize("query,expected", [("", [1, 2, 3]), ("?completed=false", [1, 3]), ("?completed=true", [2]), ("?limit=1&offset=1", [2]), ("?offset=3", [])])
def test_list_filtering_and_pagination(client, task_factory, query, expected):
    task_factory(completed=False)
    task_factory(completed=True)
    task_factory(completed=False)
    assert [task["id"] for task in client.get("/tasks" + query).json()] == expected


@pytest.mark.parametrize("query", ["?limit=0", "?limit=101", "?offset=-1", "?offset=10001", "?completed=maybe"])
def test_invalid_query(client, query):
    assert client.get("/tasks" + query).status_code == 422


@pytest.mark.parametrize("completed", [None, "true", 1, {}])
def test_patch_requires_json_boolean(client, task_factory, completed):
    task = task_factory()
    assert client.patch(f"/tasks/{task.id}", json={"completed": completed}).status_code == 422
    assert client.get(f"/tasks/{task.id}").json()["completed"] is False


@pytest.mark.parametrize("method,kwargs", [("get", {}), ("patch", {"json": {"completed": True}}), ("delete", {})])
def test_missing_task(client, method, kwargs):
    assert client.request(method, "/tasks/999", **kwargs).status_code == 404


@pytest.mark.parametrize("maximum,expected", [(0, 409), (1, 201), (2, 201)])
def test_parameterized_business_dependency(client, override_dependency, maximum, expected):
    with override_dependency(get_policy, lambda: TaskPolicy(max_tasks=maximum)):
        response = client.post("/tasks", json={"title": "policy check"})
    assert response.status_code == expected


def test_quota_override_and_restore(client, application, override_dependency, task_factory):
    original = application.dependency_overrides[get_policy]
    task_factory()
    with override_dependency(get_policy, lambda: TaskPolicy(max_tasks=1)):
        assert client.post("/tasks", json={"title": "blocked"}).status_code == 409
    assert application.dependency_overrides[get_policy] is original
    assert client.post("/tasks", json={"title": "allowed again"}).status_code == 201


def test_override_restores_after_exception(application, override_dependency):
    original = application.dependency_overrides[get_policy]
    with pytest.raises(RuntimeError):
        with override_dependency(get_policy, lambda: TaskPolicy(max_tasks=0)):
            raise RuntimeError("demonstration failure")
    assert application.dependency_overrides[get_policy] is original


def test_nested_override_restores_outer_value(application, override_dependency):
    first = lambda: TaskPolicy(max_tasks=1)
    second = lambda: TaskPolicy(max_tasks=2)
    with override_dependency(get_policy, first):
        with override_dependency(get_policy, second):
            assert application.dependency_overrides[get_policy] is second
        assert application.dependency_overrides[get_policy] is first


@pytest.mark.parametrize("unused", [1, 2], ids=["fresh-db-first", "fresh-db-second"])
def test_each_case_starts_with_empty_database(client, unused):
    assert client.get("/tasks").json() == []
    assert client.post("/tasks", json={"title": "same across cases"}).json()["id"] == 1


def test_unknown_fields_rejected(client):
    assert client.post("/tasks", json={"title": "demo", "id": 999}).status_code == 422


def test_documentation_available(client):
    assert client.get("/docs").status_code == 200
    assert "/tasks" in client.get("/openapi.json").json()["paths"]
