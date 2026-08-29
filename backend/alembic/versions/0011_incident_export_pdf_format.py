"""Add PDF support to incident export format.

Revision ID: 0011_incident_export_pdf_format
Revises: 0010_incident_export_archival
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0011_incident_export_pdf_format"
down_revision: Union[str, None] = "0010_incident_export_archival"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IncidentExportFormat enum updated in Python model with PDF.
    # SQLite/Generic String(16) format column accepts 'PDF' values.
    pass


def downgrade() -> None:
    pass
