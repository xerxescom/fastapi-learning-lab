"""受控命令行入口：角色修改不开放给注册接口。"""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import build_engine
from app.models import User


def main():
    parser = argparse.ArgumentParser(description="修改已注册用户的角色")
    parser.add_argument("username")
    parser.add_argument("--role", choices=["user", "admin"], default="admin")
    args = parser.parse_args()
    engine = build_engine(Settings().database_url)
    try:
        with Session(engine) as db:
            user = db.scalar(select(User).where(User.username == args.username.strip().lower()))
            if user is None:
                parser.error("User not found; register the user first")
            user.role = args.role
            db.commit()
        print(f"Role updated: {args.role}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
