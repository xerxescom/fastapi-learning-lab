from app.database import Base
from main import app


if __name__ == "__main__":
    try:
        Base.metadata.create_all(app.state.engine)
        print("Database initialized.")
    finally:
        app.state.engine.dispose()
