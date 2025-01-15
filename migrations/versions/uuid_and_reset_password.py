"""Add UUID for user IDs and password reset fields

Revision ID: uuid_and_reset_password
Revises: add_preferred_language
Create Date: 2024-01-14 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'uuid_and_reset_password'
down_revision = 'add_preferred_language'
branch_labels = None
depends_on = None

def upgrade():
    # Create temporary columns
    op.add_column('user', sa.Column('uuid', sa.String(36), nullable=True))
    op.add_column('quiz_result', sa.Column('user_uuid', sa.String(36), nullable=True))
    op.add_column('user', sa.Column('reset_password_token', sa.String(100), nullable=True))
    op.add_column('user', sa.Column('reset_password_expires', sa.DateTime(), nullable=True))
    
    # Create a unique index for the reset_password_token
    op.create_index(op.f('ix_user_reset_password_token'), 'user', ['reset_password_token'], unique=True)
    
    # Generate UUIDs for existing users
    connection = op.get_bind()
    users = connection.execute('SELECT id FROM "user"').fetchall()
    for user in users:
        new_uuid = str(uuid.uuid4())
        connection.execute(
            'UPDATE "user" SET uuid = :uuid WHERE id = :id',
            {'uuid': new_uuid, 'id': user[0]}
        )
        connection.execute(
            'UPDATE quiz_result SET user_uuid = :uuid WHERE user_id = :id',
            {'uuid': new_uuid, 'id': user[0]}
        )
    
    # Make uuid column not nullable
    op.alter_column('user', 'uuid', nullable=False)
    op.alter_column('quiz_result', 'user_uuid', nullable=False)
    
    # Drop old foreign key
    op.drop_constraint('quiz_result_user_id_fkey', 'quiz_result', type_='foreignkey')
    
    # Drop old primary key
    op.drop_constraint('user_pkey', 'user', type_='primary')
    
    # Drop old columns
    op.drop_column('user', 'id')
    op.drop_column('quiz_result', 'user_id')
    
    # Rename uuid columns
    op.alter_column('user', 'uuid', new_column_name='id', nullable=False)
    op.alter_column('quiz_result', 'user_uuid', new_column_name='user_id', nullable=False)
    
    # Create new primary key and foreign key
    op.create_primary_key('user_pkey', 'user', ['id'])
    op.create_foreign_key('quiz_result_user_id_fkey', 'quiz_result', 'user', ['user_id'], ['id'])

def downgrade():
    # This is a one-way migration - we can't safely convert UUIDs back to sequential integers
    raise Exception("This migration cannot be reversed. Please restore from backup if needed.") 