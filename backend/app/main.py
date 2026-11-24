from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import DomainError
from app.db.session import get_db
from app.routers import (auth, buildings, contracts, incidents, invoices, registrations, rooms,
                         statistics, users, utilities)

app = FastAPI(
    title="Hệ thống quản lý ký túc xá sinh viên",
    version="0.3.0",
    description="API quản lý tòa nhà, phòng, đăng ký phòng, hợp đồng, hóa đơn điện nước, sự cố.\n\n"
                "Bấm **Authorize**, nhập email vào ô *username* và mật khẩu để đăng nhập.",
    swagger_ui_parameters={"persistAuthorization": True},
    # Đặt dưới /api/ để Nginx chuyển tiếp được (Nginx chỉ proxy các đường dẫn bắt đầu bằng /api/)
    docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json",
)

DOC_PATHS = ("/api/docs", "/api/redoc", "/api/openapi.json")


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Các header bảo mật (tương đương Helmet bên Express)."""
    response = await call_next(request)
    h = response.headers
    path = request.url.path
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "no-referrer"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # CSP chặt cho API JSON; bỏ qua Swagger (cần tải script) và ảnh (CSP sẽ chặn hiển thị)
    if not path.startswith(DOC_PATHS) and not h.get("content-type", "").startswith("image/"):
        h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if path.startswith("/api/auth"):
        h["Cache-Control"] = "no-store"  # không cho lưu đệm token
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Thêm SAU middleware trên để CORS là lớp ngoài cùng (xử lý preflight trước)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,   # danh sách trắng, KHÔNG dùng "*"
    allow_credentials=False,                    # dùng header Authorization, không dùng cookie
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],     # để front-end đọc tên file Excel
    max_age=600,
)


@app.get("/api/health", tags=["Hệ thống"], summary="Kiểm tra API và kết nối CSDL")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "up"}


app.include_router(auth.router, prefix="/api/auth", tags=["Xác thực"])
app.include_router(users.router, prefix="/api/users", tags=["Tài khoản (Admin)"])
app.include_router(buildings.router, prefix="/api/buildings", tags=["Tòa nhà"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["Phòng"])
app.include_router(registrations.router, prefix="/api/registrations", tags=["Đăng ký phòng"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["Hợp đồng"])
app.include_router(utilities.router, prefix="/api/utilities", tags=["Điện nước"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["Hóa đơn"])
app.include_router(incidents.router, prefix="/api/incidents", tags=["Sự cố"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["Thống kê"])
