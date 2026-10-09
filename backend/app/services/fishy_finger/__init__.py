"""Weekly Fishy Finger Sub lead scrape.

Independent hospitality leads, stored on ``marketing_contacts`` with
``source_segment = fishy_finger_sub``. The Sunday job is separate from the
twice-daily deal cycles.
"""

from app.services.fishy_finger.constants import FISHY_FINGER_SEGMENT

__all__ = ["FISHY_FINGER_SEGMENT"]
