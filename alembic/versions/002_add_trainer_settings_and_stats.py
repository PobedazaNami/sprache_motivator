"""add trainer settings and stats

Revision ID: 002
Revises: 001
Create Date: 2025-11-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column('users', sa.Column('trainer_start_time', sa.String(5), server_default='09:00'))
    op.add_column('users', sa.Column('trainer_end_time', sa.String(5), server_default='21:00'))
    op.add_column('users', sa.Column('trainer_messages_per_day', sa.Integer(), server_default='3'))
    op.add_column('users', sa.Column('trainer_timezone', sa.String(50), server_default='Europe/Kiev'))
    
    # Add quality_percentage to training_sessions
    op.add_column('training_sessions', sa.Column('quality_percentage', sa.Integer()))
    
    # Create daily_stats table
    op.create_table('daily_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_tasks', sa.Integer(), server_default='0'),
        sa.Column('completed_tasks', sa.Integer(), server_default='0'),
        sa.Column('average_quality', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_daily_stats_user_id'), 'daily_stats', ['user_id'], unique=False)
    op.create_index(op.f('ix_daily_stats_date'), 'daily_stats', ['date'], unique=False)
    
    # Create weekly_stats table
    op.create_table('weekly_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('week_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_tasks', sa.Integer(), server_default='0'),
        sa.Column('completed_tasks', sa.Integer(), server_default='0'),
        sa.Column('average_quality', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weekly_stats_user_id'), 'weekly_stats', ['user_id'], unique=False)
    op.create_index(op.f('ix_weekly_stats_week_start'), 'weekly_stats', ['week_start'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f('ix_weekly_stats_week_start'), table_name='weekly_stats')
    op.drop_index(op.f('ix_weekly_stats_user_id'), table_name='weekly_stats')
    op.drop_table('weekly_stats')
    
    op.drop_index(op.f('ix_daily_stats_date'), table_name='daily_stats')
    op.drop_index(op.f('ix_daily_stats_user_id'), table_name='daily_stats')
    op.drop_table('daily_stats')
    
    # Drop columns from training_sessions
    op.drop_column('training_sessions', 'quality_percentage')
    
    # Drop columns from users
    op.drop_column('users', 'trainer_timezone')
    op.drop_column('users', 'trainer_messages_per_day')
    op.drop_column('users', 'trainer_end_time')
    op.drop_column('users', 'trainer_start_time')
