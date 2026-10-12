import asyncio
import json
from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.chat import MAX_MESSAGE_BYTES, ConnectionManager
from main import create_app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_welcome_and_echo(client: TestClient):
    with client.websocket_connect("/ws/chat?name=alice") as socket:
        welcome = socket.receive_json()
        assert welcome["type"] == "welcome" and welcome["name"] == "alice"
        assert UUID(welcome["client_id"]).version == 4
        assert welcome["online"] == 1
        socket.send_json({"type": "chat", "text": "  你好 FastAPI  "})
        assert socket.receive_json() == {"type": "chat", "sender_id": welcome["client_id"], "name": "alice", "text": "你好 FastAPI"}
        assert client.get("/health").json()["online"] == 1
    assert client.get("/health").json()["online"] == 0


def test_multiple_clients_receive_same_broadcast(client: TestClient):
    with client.websocket_connect("/ws/chat?name=alice") as alice:
        first = alice.receive_json()
        with client.websocket_connect("/ws/chat?name=bobby") as bobby:
            second = bobby.receive_json()
            assert second["online"] == 2 and first["client_id"] != second["client_id"]
            alice.send_json({"type": "chat", "text": "hello"})
            assert alice.receive_json() == bobby.receive_json()
            bobby.send_json({"type": "chat", "text": "reply"})
            expected = {"type": "chat", "sender_id": second["client_id"], "name": "bobby", "text": "reply"}
            assert alice.receive_json() == bobby.receive_json() == expected
        assert client.get("/health").json()["online"] == 1
        alice.send_json({"type": "chat", "text": "still connected"})
        assert alice.receive_json()["text"] == "still connected"
    assert client.get("/health").json()["online"] == 0


def test_same_display_name_is_not_identity(client: TestClient):
    with client.websocket_connect("/ws/chat?name=alice") as first:
        first_id = first.receive_json()["client_id"]
        with client.websocket_connect("/ws/chat?name=alice") as second:
            assert second.receive_json()["client_id"] != first_id


@pytest.mark.parametrize("query", ["", "?name=ab", "?name=UPPER", "?name=with%20space", "?name=" + "a" * 21])
def test_invalid_name_rejected_before_accept(client: TestClient, query):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws/chat" + query):
            pytest.fail("Invalid handshake must not be accepted")
    assert error.value.code == 1008
    assert client.get("/health").json()["online"] == 0


@pytest.mark.parametrize("origin", ["http://localhost:8000", "http://127.0.0.1:8000"])
def test_allowed_browser_origin(client: TestClient, origin):
    with client.websocket_connect("/ws/chat?name=alice", headers={"Origin": origin}) as socket:
        assert socket.receive_json()["type"] == "welcome"


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost:5173", "null"])
def test_disallowed_browser_origin(client: TestClient, origin):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws/chat?name=alice", headers={"Origin": origin}):
            pytest.fail("Origin must be rejected")
    assert error.value.code == 1008


@pytest.mark.parametrize("payload", [
    {}, {"type": "other", "text": "hello"}, {"type": "chat", "text": ""},
    {"type": "chat", "text": "   "}, {"type": "chat", "text": "a" * 201},
    {"type": "chat", "text": 123}, {"type": "chat", "text": "hello", "name": "forged"},
    [], None,
])
def test_invalid_message_closes_only_sender(client: TestClient, payload):
    with client.websocket_connect("/ws/chat?name=alice") as alice:
        alice.receive_json()
        with client.websocket_connect("/ws/chat?name=bobby") as bobby:
            bobby.receive_json()
            bobby.send_json(payload)
            with pytest.raises(WebSocketDisconnect) as error:
                bobby.receive_json()
            assert error.value.code == 1008
        alice.send_json({"type": "chat", "text": "still alive"})
        assert alice.receive_json()["text"] == "still alive"
    assert client.get("/health").json()["online"] == 0


def test_malformed_json(client: TestClient):
    with client.websocket_connect("/ws/chat?name=alice") as socket:
        socket.receive_json()
        socket.send_text("not json")
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 1008


@pytest.mark.parametrize("data", [b"", b"binary"])
def test_binary_message_rejected(client: TestClient, data):
    with client.websocket_connect("/ws/chat?name=alice") as socket:
        socket.receive_json()
        socket.send_bytes(data)
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 1003


def test_oversized_message(client: TestClient):
    with client.websocket_connect("/ws/chat?name=alice") as socket:
        socket.receive_json()
        socket.send_text("x" * (MAX_MESSAGE_BYTES + 1))
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 1009


def test_maximum_text_and_frame_boundary(client: TestClient):
    with client.websocket_connect("/ws/chat?name=alice") as socket:
        socket.receive_json()
        text = "你" * 200
        raw = json.dumps({"type": "chat", "text": text}, ensure_ascii=False)
        raw += " " * (MAX_MESSAGE_BYTES - len(raw.encode()))
        socket.send_text(raw)
        assert socket.receive_json()["text"] == text


def test_capacity_and_slot_reuse():
    with TestClient(create_app(capacity=1)) as client:
        with client.websocket_connect("/ws/chat?name=alice") as first:
            first.receive_json()
            with client.websocket_connect("/ws/chat?name=bobby") as second:
                with pytest.raises(WebSocketDisconnect) as error:
                    second.receive_json()
                assert error.value.code == 1013
        with client.websocket_connect("/ws/chat?name=bobby") as second:
            assert second.receive_json()["online"] == 1


class FakeSocket:
    def __init__(self):
        self.messages = []
        self.closed = []
        self.fail = False
        self.block = False

    async def send_json(self, payload):
        if self.fail:
            raise OSError("simulated disconnected transport")
        if self.block:
            await asyncio.Event().wait()
        self.messages.append(payload)

    async def close(self, code, reason):
        self.closed.append(code)


@pytest.mark.parametrize("failure", ["fail", "block"])
def test_failed_or_slow_peer_removed_without_stopping_healthy_peer(failure):
    async def run():
        manager = ConnectionManager(send_timeout=0.02)
        broken, healthy = FakeSocket(), FakeSocket()
        await manager.connect(broken, "bobby")
        sender = await manager.connect(healthy, "alice")
        setattr(broken, failure, True)
        await manager.broadcast(sender, "hello")
        assert manager.online == 1
        assert broken.closed == [1013]
        assert healthy.messages[-1]["text"] == "hello"
        await manager.broadcast(sender, "again")
        assert healthy.messages[-1]["text"] == "again"

    asyncio.run(run())


def test_welcome_send_failure_does_not_leak_connection():
    async def run():
        manager = ConnectionManager()
        socket = FakeSocket()
        socket.fail = True
        with pytest.raises(OSError):
            await manager.connect(socket, "alice")
        assert manager.online == 0

    asyncio.run(run())


def test_concurrent_broadcasts_have_same_order_for_all_peers():
    async def run():
        manager = ConnectionManager()
        sockets = [FakeSocket(), FakeSocket()]
        connections = [await manager.connect(socket, name) for socket, name in zip(sockets, ["alice", "bobby"])]
        await asyncio.gather(manager.broadcast(connections[0], "first"), manager.broadcast(connections[1], "second"))
        assert sockets[0].messages[1:] == sockets[1].messages[1:]
        manager.disconnect(connections[0].id)
        manager.disconnect(connections[0].id)
        assert manager.online == 1

    asyncio.run(run())


def test_http_docs_do_not_list_websocket_route(client: TestClient):
    assert client.get("/docs").status_code == 200
    assert "/ws/chat" not in client.get("/openapi.json").json()["paths"]
    assert client.get("/ws/chat?name=alice").status_code == 404


def test_application_instances_have_independent_connections(client: TestClient):
    with client.websocket_connect("/ws/chat?name=alice") as socket:
        socket.receive_json()
        with TestClient(create_app()) as other:
            assert other.get("/health").json()["online"] == 0
