"""Vá migration khởi tạo để downgrade xóa luôn các kiểu ENUM của PostgreSQL.

Alembic autogenerate không tự xóa kiểu ENUM khi downgrade, nên sau `downgrade base`
việc `upgrade head` lại báo: type "gender" already exists.

Chạy một lần từ thư mục backend:   python -m scripts.patch_migration
"""
import pathlib
import sys

MARK = "# vá: xóa các kiểu ENUM khi downgrade"
SNIPPET = f'''    {MARK}
    for enum_name in ("gender", "user_role", "registration_status",
                      "contract_status", "invoice_status", "incident_status"):
        op.execute(f"DROP TYPE IF EXISTS {{enum_name}}")
'''
END = "    # ### end Alembic commands ###\n"

files = sorted(pathlib.Path("alembic/versions").glob("*init_schema*.py"))
if not files:
    sys.exit("Không tìm thấy file migration *init_schema*.py trong alembic/versions")
path = files[0]
text = path.read_text(encoding="utf-8")
if MARK in text:
    sys.exit(f"{path.name} đã được vá trước đó, bỏ qua.")
pos = text.rfind(END)  # lần xuất hiện CUỐI CÙNG nằm trong hàm downgrade
if pos == -1 or "def downgrade" not in text[:pos]:
    sys.exit("Không tìm thấy vị trí cần vá trong hàm downgrade")
text = text[: pos + len(END)] + SNIPPET + text[pos + len(END):]
path.write_text(text, encoding="utf-8", newline="\n")
print(f"Đã vá {path.name}")
