"""add_user_id_to_documents

Revision ID: c8241d7e3f91
Revises: b4131a3fb826
Create Date: 2026-11-10 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8241d7e3f91'
down_revision = 'b4131a3fb826'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f('ix_documents_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documents_user_id'))
        batch_op.drop_column('user_id')

