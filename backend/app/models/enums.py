import enum


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class Role(str, enum.Enum):
    STUDENT = "STUDENT"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class RegistrationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ContractStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


class InvoiceStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"


class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
