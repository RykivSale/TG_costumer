from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_created_at_to_cart'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Добавляем колонку created_at с значением по умолчанию текущей даты
    op.add_column('cart', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))

def downgrade():
    # Удаляем колонку created_at при откате миграции
    op.drop_column('cart', 'created_at')
