from sqlalchemy.orm import Session

from .auth import hash_password
from .database import Base, SessionLocal, engine
from .database_models import User


def seed_users():
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        existing_customer = (
            db.query(User)
            .filter(
                User.email == "customer@example.com"
            )
            .first()
        )

        if not existing_customer:
            customer = User(
                name="Demo Customer",
                email="customer@example.com",
                password_hash=hash_password(
                    "customer123"
                ),
                role="customer",
            )

            db.add(customer)

        existing_agent = (
            db.query(User)
            .filter(
                User.email == "agent@example.com"
            )
            .first()
        )

        if not existing_agent:
            agent = User(
                name="Support Agent",
                email="agent@example.com",
                password_hash=hash_password(
                    "agent123"
                ),
                role="agent",
            )

            db.add(agent)

        db.commit()

        print("Demo users are ready.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_users()