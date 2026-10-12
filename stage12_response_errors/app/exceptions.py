"""业务层仅抛出业务异常，由应用层负责转成 HTTP 响应。"""


class BusinessError(Exception):
    def __init__(self, status_code: int, code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ItemNotFoundError(BusinessError):
    def __init__(self) -> None:
        super().__init__(404, 40401, "Item not found")


class OutOfStockError(BusinessError):
    def __init__(self) -> None:
        super().__init__(409, 40901, "Not enough stock")
