"""Login web controller."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from lib.ctx.auth import authenticate, send_code
from lib.exceptions import InvalidCodeError, SendCodeError, UserNotFoundError

from boundary.base.http_context import get_current_user
from boundary.base.templates import templates

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)

    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates().TemplateResponse(
        request, "login.html", {"error": None},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...)):
    try:
        send_code(email)
    except (UserNotFoundError, SendCodeError) as e:
        return templates().TemplateResponse(
            request, "login.html", {"error": str(e)},
        )

    return templates().TemplateResponse(
        request, "login_verify.html", {"email": email, "error": None},
    )


@router.post("/login/verify", response_class=HTMLResponse)
async def login_verify(request: Request, email: str = Form(...), code: str = Form(...)):
    try:
        session = authenticate(email, code)
    except (InvalidCodeError, UserNotFoundError) as e:
        return templates().TemplateResponse(
            request, "login_verify.html", {"email": email, "error": str(e)},
        )

    response = RedirectResponse(url="/", status_code=303)

    response.set_cookie(
        key="session",
        value=session.token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )

    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response
