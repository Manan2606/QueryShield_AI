from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class QueryRequest(Base):
    __tablename__ = "query_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    natural_language_question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    generation_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    validation_status: Mapped[str] = mapped_column(String, nullable=False, default="not_validated")
    is_safe: Mapped[bool | None] = mapped_column(nullable=True)
    statement_type: Mapped[str | None] = mapped_column(String, nullable=True)
    validation_errors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    validation_warnings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    referenced_tables: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="query_requests")
    dataset = relationship("Dataset", back_populates="query_requests")
