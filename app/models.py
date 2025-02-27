from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text


class Base(DeclarativeBase):
    pass


class UserValue(Base):
    __tablename__ = "uservalues"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    value_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text())


async def save_to_db(user_id: int, data: dict, session):

    value = UserValue(
        user_id=user_id,
        value_name=data["name"],
        description=data["description"]
    )
    session.add(value)
    await session.commit()