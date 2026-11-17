from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.db.session import get_db
from app.routers import (buildings, contracts, incidents, invoices, registrations, rooms,
                         statistics, utilities)

app = FastAPI(
    title="Hệ thống quản lý ký túc xá sinh viên",
    version="0.2.0",
    description="API quản lý tòa nhà, phòng, đăng ký phòng, hợp đồng, hóa đơn điện nước, sự cố.",
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/api/health", tags=["Hệ thống"], summary="Kiểm tra API và kết nối CSDL")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "up"}


app.include_router(buildings.router, prefix="/api/buildings", tags=["Tòa nhà"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["Phòng"])
app.include_router(registrations.router, prefix="/api/registrations", tags=["Đăng ký phòng"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["Hợp đồng"])
app.include_router(utilities.router, prefix="/api/utilities", tags=["Điện nước"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["Hóa đơn"])
app.include_router(incidents.router, prefix="/api/incidents", tags=["Sự cố"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["Thống kê"])
