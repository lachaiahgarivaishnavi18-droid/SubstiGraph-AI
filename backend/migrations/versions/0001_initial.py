"""Initial catalog and settings schema."""
from alembic import op
from app.database import Base
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    Base.metadata.create_all(op.get_bind())
def downgrade():
    Base.metadata.drop_all(op.get_bind())
