from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.schemas.billing import InvoiceOut
from app.schemas.statistics import OccupancyReport

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_THIN = Side(style="thin", color="BFBFBF")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_MONEY = '#,##0'


def _style_header(ws, ncols: int) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill, cell.font, cell.border = _HEADER_FILL, _HEADER_FONT, _BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"


def _autosize(ws, ncols: int) -> None:
    for col in range(1, ncols + 1):
        width = max(len(str(c.value)) if c.value is not None else 0 for c in ws[get_column_letter(col)])
        ws.column_dimensions[get_column_letter(col)].width = min(max(width + 2, 10), 40)


def _to_bytes(wb: Workbook) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def invoices_to_xlsx(invoices: list[InvoiceOut]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Hóa đơn điện nước"
    headers = ["Mã HĐ", "Tòa", "Phòng", "Kỳ (tháng/năm)", "Điện cũ", "Điện mới", "Số điện (kWh)",
               "Nước cũ", "Nước mới", "Số nước (m3)", "Tiền phòng", "Tiền điện", "Tiền nước",
               "Tổng cộng", "Trạng thái", "Hạn thanh toán", "Ngày thanh toán"]
    ws.append(headers)
    for i in invoices:
        ws.append([
            i.id, i.building_name, i.room_number, f"{i.month:02d}/{i.year}",
            i.electric_old, i.electric_new, i.electric_usage,
            i.water_old, i.water_new, i.water_usage,
            float(i.room_fee), float(i.electric_amount), float(i.water_amount), float(i.total),
            "Đã thanh toán" if i.status.value == "PAID" else "Chưa thanh toán",
            i.due_date.strftime("%d/%m/%Y"),
            i.paid_at.strftime("%d/%m/%Y %H:%M") if i.paid_at else "",
        ])
    last = len(invoices) + 1
    ws.append(["", "", "", "TỔNG CỘNG", "", "", f"=SUM(G2:G{last})", "", "", f"=SUM(J2:J{last})",
               f"=SUM(K2:K{last})", f"=SUM(L2:L{last})", f"=SUM(M2:M{last})", f"=SUM(N2:N{last})"])
    for cell in ws[last + 1]:
        cell.font = Font(bold=True)
    for row in ws.iter_rows(min_row=2, max_row=last + 1):
        for cell in row:
            cell.border = _BORDER
        for idx in (11, 12, 13, 14):  # cột K..N là tiền
            row[idx - 1].number_format = _MONEY
    _style_header(ws, len(headers))
    _autosize(ws, len(headers))
    return _to_bytes(wb)


def occupancy_to_xlsx(report: OccupancyReport) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tỷ lệ lấp đầy"
    headers = ["Tòa", "Dành cho", "Số phòng", "Tổng số giường", "Đã ở", "Còn trống", "Tỷ lệ lấp đầy (%)"]
    ws.append(headers)
    for b in report.buildings:
        ws.append([b.building_name, "Nam" if b.gender_type.value == "MALE" else "Nữ", b.total_rooms,
                   b.total_beds, b.occupied_beds, b.available_beds, b.occupancy_rate])
    ws.append(["TỔNG CỘNG", "", report.total_rooms, report.total_beds, report.occupied_beds,
               report.available_beds, report.occupancy_rate])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = _BORDER
        row[6].number_format = "0.00"
    _style_header(ws, len(headers))
    _autosize(ws, len(headers))
    return _to_bytes(wb)
