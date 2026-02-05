from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from visualizer.infra.auth import authenticate, decode_token, encode_token, send_code

router = APIRouter(tags=["auth"])

_templates: Jinja2Templates | None = None


def set_templates(templates: Jinja2Templates):
    global _templates
    _templates = templates


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("session")
    if not token:
        return None
    return decode_token(token)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return _templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...)):
    sent = send_code(email)
    if not sent:
        return _templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "No account found for that email"},
        )
    return _templates.TemplateResponse(
        "login_verify.html",
        {"request": request, "email": email, "error": None},
    )


@router.post("/login/verify", response_class=HTMLResponse)
async def login_verify(request: Request, email: str = Form(...), code: str = Form(...)):
    result = authenticate(email, code)
    if not result:
        return _templates.TemplateResponse(
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
        max_age=86400,  # 24 hours
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response
