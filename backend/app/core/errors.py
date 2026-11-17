class DomainError(Exception):
    """Lỗi nghiệp vụ: service ném ra, main.py đổi thành JSON {"detail": ...}."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
