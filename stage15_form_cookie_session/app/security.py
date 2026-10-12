"""固定演示账号不是生产账号系统，密码校验延续前面阶段的 Argon2。"""

from pwdlib import PasswordHash

DEMO_USERNAME = "learner"
DEMO_PASSWORD = "learn-fastapi-2026"
password_hasher = PasswordHash.recommended()
DEMO_PASSWORD_HASH = password_hasher.hash(DEMO_PASSWORD)


def authenticate(username: str, password: str) -> bool:
    # 不存在的用户名也做哈希校验；不直接比较明文密码。
    valid_password = password_hasher.verify(password, DEMO_PASSWORD_HASH)
    return username == DEMO_USERNAME and valid_password
