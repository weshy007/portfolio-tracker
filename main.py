"""Main FastAPI application entry point."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

from config import settings
from database import init_db
from src.api import calculations_router
from src.api.market_tracking import router as market_tracking_router
from src.api.mmf_enhancements import router as mmf_enhancements_router
from src.api.yahoo_market import router as yahoo_market_router

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

# Security middleware: add security headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Message:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; img-src 'self' data:"
        )
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Browsers reject credentialed requests with a wildcard origin.
    allow_credentials=settings.cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )

# Setup Jinja2 templates
app_dir = Path(__file__).parent / "src"
templates_dir = app_dir / "templates"
templates = Jinja2Templates(directory=templates_dir)

# Include API routes
app.include_router(calculations_router)
app.include_router(market_tracking_router)
app.include_router(mmf_enhancements_router)
app.include_router(yahoo_market_router)

# Mount static files
static_dir = app_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Template routes


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render dashboard template."""
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):
    """Render portfolio template."""
    return templates.TemplateResponse(
        request,
        "portfolio.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/budget", response_class=HTMLResponse)
async def budget(request: Request):
    """Render budget template."""
    return templates.TemplateResponse(
        request,
        "budget.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/allocation", response_class=HTMLResponse)
async def allocation(request: Request):
    """Render allocation template."""
    return templates.TemplateResponse(
        request,
        "allocation.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Render settings template."""
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"request": request, "app_name": settings.app_name},
    )


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.app_env,
    }


# Root endpoint (redirects to dashboard)
@app.get("/api/")
async def api_root():
    """API root endpoint."""
    return {"message": f"Welcome to {settings.app_name} API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
