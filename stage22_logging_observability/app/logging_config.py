"""仅配置本阶段的 logger，不覆盖 Uvicorn 或宿主应用日志。"""

import json
import logging
from datetime import datetime, timezone

LOGGER_NAME = "stage22"
FIELDS = ("request_id", "method", "route", "status_code", "duration_ms", "failed", "error_type")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for field in FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        # 不附加 exc_info、任意 extra 或异常消息，避免意外记录敏感输入。
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(getattr(handler, "stage22_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.stage22_handler = True
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger
