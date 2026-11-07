"""Add repair domain, RBAC and append-only audit/price lock.

Revision ID: a726bdf3c001
Revises: fe56fa70289e
"""

from alembic import op
import sqlalchemy as sa

from app.domain_models import (
    ChannelIdentity, DeliveryLeg, DeliveryProofPhoto, DeliveryTariff, EstimateVersion, EventLog,
    Garment, GarmentPhoto, IntakeDraft, MasterLinkCode, MasterProfile, Payment, PriceLock, RepairOrder,
)

revision = "a726bdf3c001"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None

TABLES = [MasterProfile, RepairOrder, Garment, GarmentPhoto, DeliveryLeg, DeliveryProofPhoto, DeliveryTariff,
          EstimateVersion, PriceLock, Payment, EventLog, ChannelIdentity, IntakeDraft, MasterLinkCode]


def upgrade() -> None:
    op.add_column("user", sa.Column("role", sa.String(length=16), nullable=False, server_default="customer"))
    op.add_column("user", sa.Column("receipt_email", sa.String(length=255), nullable=True))
    op.add_column("user", sa.Column("phone", sa.String(length=20), nullable=True))
    op.create_index("ix_user_role", "user", ["role"])
    op.create_check_constraint("user_valid_role", "user", "role IN ('owner','operator','master','courier','customer')")
    op.execute("UPDATE \"user\" SET role='owner' WHERE is_superuser = TRUE")
    bind = op.get_bind()
    for model in TABLES:
        model.__table__.create(bind)
    for table in ("estimate_version", "price_lock", "event_log"):
        op.execute(f"""
            CREATE FUNCTION {table}_immutable_guard() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '{table} is append-only';
            END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION {table}_immutable_guard();
        """)


def downgrade() -> None:
    for table in ("event_log", "price_lock", "estimate_version"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
        op.execute(f"DROP FUNCTION IF EXISTS {table}_immutable_guard()")
    bind = op.get_bind()
    for model in reversed(TABLES):
        model.__table__.drop(bind)
    op.drop_constraint("user_valid_role", "user", type_="check")
    op.drop_index("ix_user_role", table_name="user")
    op.drop_column("user", "role")
    op.drop_column("user", "receipt_email")
    op.drop_column("user", "phone")
