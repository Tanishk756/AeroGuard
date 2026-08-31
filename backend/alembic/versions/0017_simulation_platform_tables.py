"""Migration 0017: Create simulation_scenarios and simulation_runs tables for Stage S1 simulation platform.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-31 12:15:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0017_simulation_platform_tables'
down_revision: Union[str, None] = '0016_login_lockout_security'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'simulation_scenarios',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('configuration_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('configuration_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('scenario_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='CREATED'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('stopped_at', sa.DateTime(), nullable=True),
        sa.Column('telemetry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('artifact_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['scenario_id'], ['simulation_scenarios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('simulation_runs')
    op.drop_table('simulation_scenarios')
