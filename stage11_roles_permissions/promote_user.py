"""本地管理员引导命令，只修改已存在用户的角色。"""

import argparse

from sqlalchemy import select

from app.database import SessionLocal, engine
from app.models import User
from app.permissions import Role


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="将本阶段已有用户设置为管理员")
    parser.add_argument("username", help="已经注册的用户名")
    args = parser.parse_args(argv)
    username = args.username.strip().lower()
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            print("用户不存在，请先注册。")
            return 1
        user.role = Role.ADMIN
        session.commit()
    print(f"用户 {username} 已设为管理员。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        engine.dispose()
