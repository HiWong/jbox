"""empty message

Revision ID: 8a49d733d502
Revises: ba2804042b42
Create Date: 2016-10-11 17:04:19.904075

"""

# revision identifiers, used by Alembic.
revision = '8a49d733d502'
down_revision = 'ba2804042b42'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('githubs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('integration_id', sa.Integer(), nullable=True),
    sa.Column('repository', sa.String(length=150), nullable=True),
    sa.ForeignKeyConstraint(['integration_id'], ['integrations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('githubs')
    ### end Alembic commands ###
