import time
from tasks.journey.base_page   import BasePage
from api.study_details_api     import StudyDetailsAPI
from utils.logger import get_logger
logger = get_logger(__name__)

class StudyDetailsPage(BasePage):
    """
    Page 4 — Study Details
    Operations: API calls only — no file upload or download
    No polling required.
    """

    PAGE_KEY = "study_details_page"

    def __init__(self, client, environment, profile, study_id):
        super().__init__(client, environment, profile, study_id)
        self.api = StudyDetailsAPI(self.client)          # ← instantiate once

    def execute(self):
        page_start = time.monotonic()

        logger.info(f"📋  [{self.PAGE_KEY}][{self.profile['profile_name']}] "
              f"Loading study details for study_id: {self.study_id}")

        # ── API call 1 — study details ─────────────────────────────────────
        response_details = self.api.get_details(
            study_id = self.study_id,
            name     = self._name("GET", "/api/study/details/{study_id}")
        )

        if response_details.status_code != 200:
            logger.error(f"❌  [{self.PAGE_KEY}] get_details failed: "
                  f"{response_details.status_code}")

        # ── API call 2 — study summary ─────────────────────────────────────
        response_summary = self.api.get_summary(
            study_id = self.study_id,
            name     = self._name("GET", "/api/study/summary/{study_id}")
        )

        if response_summary.status_code != 200:
            logger.error(f"❌  [{self.PAGE_KEY}] get_summary failed: "
                  f"{response_summary.status_code}")

        elapsed_ms = (time.monotonic() - page_start) * 1000

        # ── Fire page-level event ──────────────────────────────────────────
        self._fire_page_event(elapsed_ms = elapsed_ms)

        print(f"✅  [{self.PAGE_KEY}] Page complete — "
              f"elapsed: {elapsed_ms:.0f}ms")