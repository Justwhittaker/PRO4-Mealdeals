"""Weekly New Business Outreach.

Finds restaurants, takeaways, and cellar-door wine venues that are not
already on DineADeal and stores a lean row on ``marketing_contacts`` with
``source_segment = new_business_outreach``. The Sunday job does not send email.
"""

from app.services.new_business_outreach.constants import NEW_BUSINESS_SEGMENT

__all__ = ["NEW_BUSINESS_SEGMENT"]
