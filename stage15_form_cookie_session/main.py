"""Stage 15：表单、普通 Cookie 与服务端 Session。"""

from secrets import compare_digest
from typing import Annotated, Literal

from fastapi import Cookie, Depends, FastAPI, Form, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import Settings
from app.security import authenticate
from app.sessions import Session, SessionStore

SESSION_COOKIE = "lab_session"
THEME_COOKIE = "lab_theme"


class CsrfResponse(BaseModel):
    csrf_token: str


class LoginResponse(CsrfResponse):
    username: str


class UserResponse(BaseModel):
    username: str


class ThemeResponse(BaseModel):
    theme: Literal["light", "dark"]


def create_app(settings: Settings | None = None, *, store: SessionStore | None = None) -> FastAPI:
    settings = settings or Settings()
    store = store or SessionStore(settings.session_ttl_seconds)
    application = FastAPI(title="Stage 15：表单、Cookie 与 Session")

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # 默认 422 可能包含原始 input；登录参数错误时不能回显密码或 Cookie。
        errors = [{"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors}, headers={"Cache-Control": "no-store"})

    def set_session_cookie(response: Response, session: Session) -> None:
        response.set_cookie(
            SESSION_COOKIE, session.session_id, max_age=store.ttl, path="/",
            httponly=True, secure=settings.cookie_secure, samesite="lax",
        )
        response.headers["Cache-Control"] = "no-store"

    def current_session(session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> Session:
        session = store.get(session_id)
        if session is None:
            raise HTTPException(401, "Session missing or expired", headers={"Cache-Control": "no-store"})
        return session

    def require_csrf(
        session: Annotated[Session, Depends(current_session)],
        csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    ) -> Session:
        # 使用字节比较，非 ASCII 的恶意 Header 也不会导致 TypeError。
        if csrf_token is None or not compare_digest(csrf_token.encode(), session.csrf_token.encode()):
            raise HTTPException(403, "Invalid CSRF token", headers={"Cache-Control": "no-store"})
        return session

    @application.get("/auth/csrf", response_model=CsrfResponse, tags=["session"])
    def csrf(
        response: Response,
        session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
    ) -> CsrfResponse:
        response.headers["Cache-Control"] = "no-store"
        session = store.get(session_id)
        if session is None:
            session = store.create()
            set_session_cookie(response, session)
        return CsrfResponse(csrf_token=session.csrf_token)

    @application.post("/auth/login", response_model=LoginResponse, tags=["session"])
    def login(
        response: Response,
        session: Annotated[Session, Depends(require_csrf)],
        username: Annotated[str, Form(min_length=1, max_length=50)],
        password: Annotated[str, Form(min_length=1, max_length=128)],
    ) -> LoginResponse:
        if not authenticate(username, password):
            raise HTTPException(401, "Invalid username or password", headers={"Cache-Control": "no-store"})
        # 认证成功后同时轮换会话 ID 和 CSRF Token，避免沿用匿名会话。
        session = store.create(username=username, previous_id=session.session_id)
        set_session_cookie(response, session)
        return LoginResponse(username=username, csrf_token=session.csrf_token)

    @application.get("/auth/me", response_model=UserResponse, tags=["session"])
    def me(response: Response, session: Annotated[Session, Depends(current_session)]) -> UserResponse:
        if session.username is None:
            raise HTTPException(401, "Login required", headers={"Cache-Control": "no-store"})
        response.headers["Cache-Control"] = "no-store"
        return UserResponse(username=session.username)

    @application.post("/auth/logout", tags=["session"])
    def logout(response: Response, session: Annotated[Session, Depends(require_csrf)]) -> dict[str, str]:
        store.delete(session.session_id)
        response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=settings.cookie_secure, samesite="lax")
        response.headers["Cache-Control"] = "no-store"
        return {"message": "Logged out"}

    @application.get("/cookies/theme", response_model=ThemeResponse, tags=["cookie"])
    def read_theme(response: Response, theme: Annotated[Literal["light", "dark"], Cookie(alias=THEME_COOKIE)] = "light") -> ThemeResponse:
        response.headers["Cache-Control"] = "no-store"
        return ThemeResponse(theme=theme)

    @application.post("/cookies/theme", response_model=ThemeResponse, tags=["cookie"])
    def set_theme(
        response: Response,
        session: Annotated[Session, Depends(require_csrf)],
        theme: Annotated[Literal["light", "dark"], Form()],
    ) -> ThemeResponse:
        # 偏好数据可被客户端修改，不能作为用户身份或权限来源。
        response.set_cookie(THEME_COOKIE, theme, max_age=86400, path="/", secure=settings.cookie_secure, samesite="lax")
        response.headers["Cache-Control"] = "no-store"
        return ThemeResponse(theme=theme)

    @application.delete("/cookies/theme", response_model=ThemeResponse, tags=["cookie"])
    def delete_theme(response: Response, session: Annotated[Session, Depends(require_csrf)]) -> ThemeResponse:
        response.delete_cookie(THEME_COOKIE, path="/", secure=settings.cookie_secure, samesite="lax")
        response.headers["Cache-Control"] = "no-store"
        return ThemeResponse(theme="light")

    return application


app = create_app()
