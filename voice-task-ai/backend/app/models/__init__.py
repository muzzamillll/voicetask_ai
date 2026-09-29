"""
Import every model here so that app.database.database.Base.metadata
is fully populated — this is what Alembic's autogenerate relies on.
"""
from app.models.user import User          # noqa: F401
from app.models.voice_note import VoiceNote  # noqa: F401
from app.models.transcript import Transcript  # noqa: F401
from app.models.task import Task          # noqa: F401
from app.models.order import Order        # noqa: F401
from app.models.payment import Payment    # noqa: F401
from app.models.contact import Contact    # noqa: F401

from app.models.slack_event import SlackEvent  # noqa: F401
