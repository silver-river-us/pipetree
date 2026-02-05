import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from visualizer.infra.models import Tenant, User

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()

ADMIN_USERNAME = "silver"
ADMIN_PASSWORD = "river"

# Will be set by register function
_templates: Jinja2Templates | None = None


def set_templates(templates: Jinja2Templates):
    global _templates
    _templates = templates


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
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
    tenants = list(Tenant.select())
    return _templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "tenants": tenants},
    )


@router.get("/tenants/new", response_class=HTMLResponse)
async def new_tenant_form(request: Request, _: str = Depends(verify_admin)):
    return _templates.TemplateResponse(
        "admin/tenant_form.html",
        {"request": request, "error": None},
    )


@router.post("/tenants", response_class=HTMLResponse)
async def create_tenant(
    request: Request,
    name: str = Form(...),
    db_name: str = Form(""),
    _: str = Depends(verify_admin),
):
    import re
    from uuid import uuid4

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    api_key = uuid4().hex + uuid4().hex[:32]
    if not db_name:
        db_name = slug

    Tenant.create(name=name, slug=slug, api_key=api_key, db_name=db_name)
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/tenants/{tenant_id}", response_class=HTMLResponse)
async def tenant_detail(request: Request, tenant_id: str, _: str = Depends(verify_admin)):
    tenant = Tenant.get_or_none(Tenant.id == tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = list(User.select().where(User.tenant == tenant_id))
    return _templates.TemplateResponse(
        "admin/tenant_detail.html",
        {"request": request, "tenant": tenant, "users": users},
    )


@router.get("/tenants/{tenant_id}/users/new", response_class=HTMLResponse)
async def new_user_form(request: Request, tenant_id: str, _: str = Depends(verify_admin)):
    tenant = Tenant.get_or_none(Tenant.id == tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return _templates.TemplateResponse(
        "admin/user_form.html",
        {"request": request, "tenant": tenant, "error": None},
    )


@router.post("/tenants/{tenant_id}/users", response_class=HTMLResponse)
async def create_user(
    request: Request,
    tenant_id: str,
    email: str = Form(...),
    _: str = Depends(verify_admin),
):
    tenant = Tenant.get_or_none(Tenant.id == tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing = User.get_or_none(User.email == email.lower().strip())
    if existing:
        return _templates.TemplateResponse(
            "admin/user_form.html",
            {"request": request, "tenant": tenant, "error": "Email already exists"},
            status_code=400,
        )

    User.create(email=email, tenant=tenant)
    return RedirectResponse(url=f"/admin/tenants/{tenant_id}", status_code=303)


@router.post("/tenants/{tenant_id}/delete", response_class=HTMLResponse)
async def delete_tenant(
    request: Request,
    tenant_id: str,
    _: str = Depends(verify_admin),
):
    tenant = Tenant.get_or_none(Tenant.id == tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    User.delete().where(User.tenant == tenant_id).execute()
    tenant.delete_instance()
    return RedirectResponse(url="/admin", status_code=303)
