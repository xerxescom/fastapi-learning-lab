"""容器内探针：仅访问回环地址，不需要额外安装 curl。"""

import json
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


def check_health(url: str = "http://127.0.0.1:8000/health/ready") -> bool:
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(url, timeout=2) as response:
            return response.status == 200 and json.load(response) == {"status": "ready"}
    except (URLError, OSError, ValueError):
        return False


if __name__ == "__main__":
    raise SystemExit(0 if check_health() else 1)
