from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    # Provision the first owner only from deployment-provided secrets. Never seed a
    # known demo password or silently reset an existing owner's credentials.
    if not settings.OWNER_EMAIL or not settings.OWNER_PASSWORD:
        return
    user = session.exec(select(User).where(User.email == settings.OWNER_EMAIL)).first()
    if not user:
        user_in = UserCreate(
            email=settings.OWNER_EMAIL,
            password=settings.OWNER_PASSWORD,
            is_superuser=True,
            role="owner",
        )
        crud.create_user(session=session, user_create=user_in)
