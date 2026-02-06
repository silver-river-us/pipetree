"""Login web controller."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from visualizer.lib.auth import authenticate, encode_token, get_current_user, send_code

from .shared import templates

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates().TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...)):
    sent = send_code(email)
    if not sent:
        return templates().TemplateResponse(
            "login.html",
            {"request": request, "error": "No account found for that email"},
        )
    return templates().TemplateResponse(
        "login_verify.html",
        {"request": request, "email": email, "error": None},
    )


@router.post("/login/verify", response_class=HTMLResponse)
async def login_verify(request: Request, email: str = Form(...), code: str = Form(...)):
    result = authenticate(email, code)
    if not result:
        return templates().TemplateResponse(
            "login_verify.html",
            {"request": request, "email": email, "error": "Invalid or expired code"},
        )

    token = encode_token(result["user_id"], result["email"], result["tenant_id"])
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="session",
        value=token,
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
