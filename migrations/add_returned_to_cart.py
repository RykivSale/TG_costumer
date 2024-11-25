from sqlalchemy import Boolean, Column
from alembic import op

# Добавление поля returned в таблицу cart
def upgrade():
    op.add_column('cart', Column('returned', Boolean, nullable=False, server_default='false'))

# Удаление поля returned из таблицы cart
def downgrade():
    op.drop_column('cart', 'returned')
