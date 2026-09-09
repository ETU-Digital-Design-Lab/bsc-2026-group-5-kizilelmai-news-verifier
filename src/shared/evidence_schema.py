"""Provenance columns for new tables; existing tables require the additive migration."""
from sqlalchemy import Column, Text, DateTime, text


class EvidenceColumns:
    source_url = Column(Text, nullable=True)
    publisher = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    evidence_id = Column(Text, nullable=True)
    label_provenance = Column(Text, nullable=False, server_default=text("'unknown'"))
    ingested_at = Column(DateTime(timezone=True), nullable=True)
