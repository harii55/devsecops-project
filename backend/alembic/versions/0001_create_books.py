import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "books",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("genre", sa.String(60), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("borrower", sa.String(120)),
    )


def downgrade():
    op.drop_table("books")
