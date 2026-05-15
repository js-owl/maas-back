from http.cookies import SimpleCookie
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from backend import schemas
from backend.auth import router as auth_router
from backend.auth.service import decode_refresh_token, get_refresh_session_key


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    async def set(self, key, value, ex=None):
        self.values[key] = value
        self.ttls[key] = ex

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)
        self.ttls.pop(key, None)


class FakeResult:
    def __init__(self, user):
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class FakeDb:
    def __init__(self, user):
        self.user = user

    async def execute(self, _statement):
        return FakeResult(self.user)


def make_user(username="session_user"):
    return SimpleNamespace(
        username=username,
        is_admin=False,
        must_change_password=False,
        status="active",
    )


def refresh_cookie_value(response: Response) -> str:
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie["refresh_token"].value


@pytest.mark.asyncio
async def test_login_sets_refresh_cookie_and_returns_access_token(monkeypatch):
    user = make_user()
    redis = FakeRedis()

    async def fake_authenticate_user(_db, username, _password):
        assert username == user.username
        return user

    monkeypatch.setattr(auth_router, "authenticate_user", fake_authenticate_user)

    response = Response()
    body = await auth_router.login(
        schemas.UserLogin(username=user.username, password="secret", remember_me=True),
        response,
        db=FakeDb(user),
        redis=redis,
    )

    assert body.access_token
    assert body.token_type == "bearer"
    assert "refresh_token=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Max-Age=" in response.headers["set-cookie"]
    assert len(redis.values) == 1


@pytest.mark.asyncio
async def test_refresh_rotates_refresh_session(monkeypatch):
    user = make_user()
    redis = FakeRedis()

    async def fake_authenticate_user(_db, _username, _password):
        return user

    monkeypatch.setattr(auth_router, "authenticate_user", fake_authenticate_user)

    login_response = Response()
    await auth_router.login(
        schemas.UserLogin(username=user.username, password="secret", remember_me=False),
        login_response,
        db=FakeDb(user),
        redis=redis,
    )
    old_refresh_token = refresh_cookie_value(login_response)
    old_payload = decode_refresh_token(old_refresh_token)

    refresh_response = Response()
    body = await auth_router.refresh(
        refresh_response,
        refresh_token=old_refresh_token,
        db=FakeDb(user),
        redis=redis,
    )

    new_refresh_token = refresh_cookie_value(refresh_response)
    assert body.access_token
    assert new_refresh_token != old_refresh_token
    assert await redis.get(get_refresh_session_key(old_payload["jti"])) is None

    with pytest.raises(HTTPException) as exc_info:
        await auth_router.refresh(
            Response(),
            refresh_token=old_refresh_token,
            db=FakeDb(user),
            redis=redis,
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_session(monkeypatch):
    user = make_user()
    redis = FakeRedis()

    async def fake_authenticate_user(_db, _username, _password):
        return user

    monkeypatch.setattr(auth_router, "authenticate_user", fake_authenticate_user)

    login_response = Response()
    await auth_router.login(
        schemas.UserLogin(username=user.username, password="secret"),
        login_response,
        db=FakeDb(user),
        redis=redis,
    )
    refresh_token = refresh_cookie_value(login_response)
    payload = decode_refresh_token(refresh_token)

    logout_response = Response()
    result = await auth_router.logout(logout_response, refresh_token=refresh_token, redis=redis)

    assert result.message == "Successfully logged out"
    assert await redis.get(get_refresh_session_key(payload["jti"])) is None
    assert "refresh_token=" in logout_response.headers["set-cookie"]

    with pytest.raises(HTTPException) as exc_info:
        await auth_router.refresh(
            Response(),
            refresh_token=refresh_token,
            db=FakeDb(user),
            redis=redis,
        )
    assert exc_info.value.status_code == 401
