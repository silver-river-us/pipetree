"""Admin web controller."""

import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from lib.ctx import identity as identity_lib
from lib.exceptions import TenantNotFoundError

from boundary.base.templates import templates

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()
require_basic = Depends(security)

ADMIN_USERNAME = "silver"
ADMIN_PASSWORD = "river"


def verify_admin(credentials: HTTPBasicCredentials = require_basic) -> str:
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, _: str = Depends(verify_admin)):
    tenants = identity_lib.list_tenants()

    return templates().TemplateResponse(
        request, "admin/dashboard.html", {"tenants": tenants},
    )


@router.get("/tenants/new", response_class=HTMLResponse)
async def new_tenant_form(request: Request, _: str = Depends(verify_admin)):
    return templates().TemplateResponse(
        request, "admin/tenant_form.html", {"error": None},
    )


@router.post("/tenants", response_class=HTMLResponse)
async def create_tenant(
    request: Request,
    name: str = Form(...),
    db_name: str = Form(""),
    _: str = Depends(verify_admin),
):
    identity_lib.create_tenant(name, db_name)
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/tenants/{tenant_id}", response_class=HTMLResponse)
async def tenant_detail(
    request: Request, tenant_id: str, _: str = Depends(verify_admin)
):
    tenant = identity_lib.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = identity_lib.list_users_for_tenant(tenant_id)

    return templates().TemplateResponse(
        request, "admin/tenant_detail.html", {"tenant": tenant, "users": users},
    )


@router.get("/tenants/{tenant_id}/users/new", response_class=HTMLResponse)
async def new_user_form(
    request: Request, tenant_id: str, _: str = Depends(verify_admin)
):
    tenant = identity_lib.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return templates().TemplateResponse(
        request, "admin/user_form.html", {"tenant": tenant, "error": None},
    )


@router.post("/tenants/{tenant_id}/users", response_class=HTMLResponse)
async def create_user(
    request: Request,
    tenant_id: str,
    email: str = Form(...),
    _: str = Depends(verify_admin),
):
    tenant = identity_lib.get_tenant(tenant_id)

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing = identity_lib.get_user_by_email(email)

    if existing:
        return templates().TemplateResponse(
            request,
            "admin/user_form.html",
            {"tenant": tenant, "error": "Email already exists"},
            status_code=400,
        )

    identity_lib.create_user(email, tenant)
    return RedirectResponse(url=f"/admin/tenants/{tenant_id}", status_code=303)


@router.post("/tenants/{tenant_id}/delete", response_class=HTMLResponse)
async def delete_tenant(
    request: Request,
    tenant_id: str,
    _: str = Depends(verify_admin),
):
    try:
        identity_lib.delete_tenant(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return RedirectResponse(url="/admin", status_code=303)
