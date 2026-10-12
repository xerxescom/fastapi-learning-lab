import asyncio
import json
import logging
from collections.abc import Generator
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.schemas import UserCreate
from app.state import LabState
from app.tasks import send_welcome_email
from main import create_app


@pytest.fixture
def state() -> LabState:
    return LabState()


@pytest.fixture
def client(state: LabState) -> Generator[TestClient, None, None]:
    with TestClient(create_app(state=state)) as test_client:
        yield test_client


def register(client: TestClient, username="learner", email="learner@example.com"):
    return client.post("/users", json={"username": username, "email": email})


def test_registration_returns_pending_snapshot(client: TestClient):
    response = register(client)
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["user"] == {"id": 1, "username": "learner", "email": "learner@example.com"}
    notification = body["notification"]
    assert UUID(notification["id"]).version == 4
    assert notification["user_id"] == 1 and notification["status"] == "pending"
    assert notification["attempts"] == 0 and notification["error"] is None
    # TestClient 等待 ASGI 调用结束，因此后续查询时后台任务已经完成。
    current = client.get(f'/notifications/{notification["id"]}').json()
    assert current["status"] == "succeeded" and current["attempts"] == 1
    assert current["error"] is None


def test_mail_parameters_and_outbox(client: TestClient):
    body = register(client, username="alice", email="alice@example.com").json()
    mails = client.get("/demo/outbox").json()
    assert mails == [{
        "notification_id": body["notification"]["id"],
        "recipient": "alice@example.com",
        "subject": "Welcome to FastAPI Learning Lab",
        "body": "Hello alice, your demo registration is complete.",
    }]


def test_sender_injection_receives_correct_arguments(state: LabState):
    captured = []
    with TestClient(create_app(state=state, sender=captured.append)) as client:
        body = register(client).json()
    assert len(captured) == 1
    mail = captured[0]
    assert str(mail.notification_id) == body["notification"]["id"]
    assert mail.recipient == "learner@example.com"
    assert "learner" in mail.body


def test_failure_does_not_rollback_registration(client: TestClient, caplog):
    response = register(client, email="fail@example.com")
    assert response.status_code == 201
    body = response.json()
    assert client.get(f'/users/{body["user"]["id"]}').json() == body["user"]
    notification = client.get(f'/notifications/{body["notification"]["id"]}').json()
    assert notification["status"] == "failed" and notification["attempts"] == 1
    assert notification["error"] == "Notification delivery failed"
    assert client.get("/demo/outbox").json() == []
    records = [record for record in caplog.records if record.name == "stage17.notifications"]
    assert len(records) == 1 and records[0].levelno == logging.ERROR
    assert body["notification"]["id"] in records[0].getMessage()
    assert "fail@example.com" not in records[0].getMessage()
    assert "transport failure" not in response.text + json.dumps(notification)


def test_success_logs_only_notification_id(client: TestClient, caplog):
    body = register(client).json()
    records = [record for record in caplog.records if record.name == "stage17.notifications"]
    assert len(records) == 1 and records[0].levelno == logging.INFO
    assert body["notification"]["id"] in records[0].getMessage()
    assert "learner@example.com" not in records[0].getMessage()


@pytest.mark.parametrize("username,email", [("learner", "other@example.com"), ("another", "learner@example.com"), ("another", "LEARNER@EXAMPLE.COM")])
def test_duplicate_registration_does_not_schedule_more_mail(client: TestClient, username, email):
    assert register(client).status_code == 201
    assert register(client, username, email).status_code == 409
    assert len(client.get("/demo/outbox").json()) == 1


@pytest.mark.parametrize("body", [
    {}, {"username": "learner"}, {"email": "a@example.com"},
    {"username": "ab", "email": "a@example.com"},
    {"username": "UPPER", "email": "a@example.com"},
    {"username": "a" * 31, "email": "a@example.com"},
    {"username": "with space", "email": "a@example.com"},
    {"username": "learner", "email": "not-an-email"},
    {"username": "learner", "email": "a@example.com", "password": "not-accepted"},
])
def test_invalid_registration_does_not_send(client: TestClient, body):
    assert client.post("/users", json=body).status_code == 422
    assert client.get("/demo/outbox").json() == []
    assert client.get("/users/1").status_code == 404


def test_username_whitespace_normalized(client: TestClient):
    body = register(client, username=" learner ").json()
    assert body["user"]["username"] == "learner"
    assert "Hello learner," in client.get("/demo/outbox").json()[0]["body"]


@pytest.mark.parametrize("path,status", [("/users/99", 404), ("/users/not-int", 422), (f"/notifications/{uuid4()}", 404), ("/notifications/not-uuid", 422)])
def test_missing_or_invalid_resources(client: TestClient, path, status):
    assert client.get(path).status_code == status


def test_multiple_users_keep_task_parameters_separate(client: TestClient):
    first = register(client, "alice", "alice@example.com").json()
    second = register(client, "bobby", "bobby@example.com").json()
    assert first["user"]["id"] == 1 and second["user"]["id"] == 2
    assert first["notification"]["id"] != second["notification"]["id"]
    mails = client.get("/demo/outbox").json()
    assert [mail["recipient"] for mail in mails] == ["alice@example.com", "bobby@example.com"]
    assert "alice" in mails[0]["body"] and "bobby" in mails[1]["body"]


def test_repeat_task_does_not_send_twice(state: LabState):
    user, notification = state.register(UserCreate(username="learner", email="learner@example.com"))
    kwargs = dict(notification_id=notification.id, recipient=user.email, username=user.username, state=state, sender=state.send_demo_mail)
    send_welcome_email(**kwargs)
    send_welcome_email(**kwargs)
    assert len(state.outbox()) == 1
    assert state.get_notification(notification.id).attempts == 1


def test_failed_notification_is_not_automatically_retried(state: LabState):
    user, notification = state.register(UserCreate(username="learner", email="fail@example.com"))
    kwargs = dict(notification_id=notification.id, recipient=user.email, username=user.username, state=state, sender=state.send_demo_mail)
    send_welcome_email(**kwargs)
    send_welcome_email(**kwargs)
    assert state.get_notification(notification.id).status == "failed"
    assert state.get_notification(notification.id).attempts == 1


def test_response_sent_before_blocked_background_task_completes():
    state = LabState()
    task_started = Event()
    release_task = Event()

    def blocking_sender(mail):
        task_started.set()
        if not release_task.wait(timeout=5):
            raise TimeoutError("Test failed to release sender")

    application = create_app(state=state, sender=blocking_sender)

    async def run():
        body = json.dumps({"username": "learner", "email": "learner@example.com"}).encode()
        messages = []
        response_sent = asyncio.Event()
        received = False

        async def receive():
            nonlocal received
            if not received:
                received = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                response_sent.set()

        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http", "path": "/users", "raw_path": b"/users", "query_string": b"", "root_path": "", "headers": [(b"content-type", b"application/json")], "client": ("testclient", 123), "server": ("testserver", 80)}
        call = asyncio.create_task(application(scope, receive, send))
        try:
            await asyncio.wait_for(response_sent.wait(), timeout=3)
            assert await asyncio.to_thread(task_started.wait, 3)
            assert not call.done()
            assert next(message for message in messages if message["type"] == "http.response.start")["status"] == 201
            result = json.loads(b"".join(message.get("body", b"") for message in messages))
            notification_id = UUID(result["notification"]["id"])
            assert result["notification"]["status"] == "pending"
            assert state.get_notification(notification_id).status == "running"
        finally:
            release_task.set()
            await asyncio.wait_for(call, timeout=3)
        assert state.get_notification(notification_id).status == "succeeded"

    asyncio.run(run())


def test_background_tasks_run_in_registration_order():
    events = []
    tasks = BackgroundTasks()
    tasks.add_task(events.append, "first")
    tasks.add_task(events.append, "second")
    asyncio.run(tasks())
    assert events == ["first", "second"]


def test_uncaught_task_error_stops_later_tasks():
    events = []

    def fail():
        events.append("first")
        raise RuntimeError("uncaught task failure")

    tasks = BackgroundTasks()
    tasks.add_task(fail)
    tasks.add_task(events.append, "second")
    with pytest.raises(RuntimeError, match="uncaught task failure"):
        asyncio.run(tasks())
    assert events == ["first"]


def test_demo_capacity_limit():
    with TestClient(create_app(state=LabState(capacity=1))) as client:
        assert register(client).status_code == 201
        assert register(client, "another", "another@example.com").status_code == 503
        assert len(client.get("/demo/outbox").json()) == 1


def test_application_instances_do_not_share_state(client: TestClient):
    register(client)
    with TestClient(create_app()) as other:
        assert other.get("/users/1").status_code == 404
        assert other.get("/demo/outbox").json() == []


def test_openapi_documents_registration_and_status(client: TestClient):
    schema = client.get("/openapi.json").json()
    assert "201" in schema["paths"]["/users"]["post"]["responses"]
    assert "/notifications/{notification_id}" in schema["paths"]
    assert schema["components"]["schemas"]["NotificationRead"]["properties"]["status"]["enum"] == ["pending", "running", "succeeded", "failed"]
