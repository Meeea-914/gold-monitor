"""Add not NULL constraint to host column of harvester_events table

Revision ID: ea982cfdfbf8
Revises: 10bc373fc537
Create Date: 2021-07-13 18:12:19.000355

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'ea982cfdfbf8'
down_revision = '10bc373fc537'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('harvester_events', schema=None) as batch_op:
        batch_op.alter_column('host',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('harvester_events', schema=None) as batch_op:
        batch_op.alter_column('host',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)

    # ### end Alembic commands ###
