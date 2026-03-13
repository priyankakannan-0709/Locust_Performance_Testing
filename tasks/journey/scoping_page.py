import time
from tasks.journey.base_page  import BasePage
from api.scoping_api          import ScopingAPI
from utils.polling_engine     import PollingEngine, STATUS_COMPLETED
from utils.logger import get_logger
logger = get_logger(__name__)

class ScopingPage(BasePage):
    """
    Page 3 — Scoping
    Operations: download only
    No file upload — download triggers artifact job, polled until complete.
    """

    PAGE_KEY = "scoping_page"

    def __init__(self, client, environment, profile, study_id):
        super().__init__(client, environment, profile, study_id)
        self.api = ScopingAPI(self.client)               # ← instantiate once

    def execute(self):
        page_start = time.monotonic()

        self._execute_download()

        self._fire_page_event(
            elapsed_ms = (time.monotonic() - page_start) * 1000
        )

    def _execute_download(self):
        start = time.monotonic()

        logger.info(f"📥  [{self.PAGE_KEY}][{self.profile['profile_name']}] "
              f"Downloading for study_id: {self.study_id}")

        response = self.api.download(
            study_id = self.study_id,
            name     = self._name("GET", "/api/scoping/download/{study_id}")
        )

        if response.status_code != 200:
            logger.error(f"❌  [{self.PAGE_KEY}] Download failed: "
                  f"{response.status_code}")
            return

        # ── STUB — extract job_id from response ────────────────────────────
        job_id = "STUB_DOWNLOAD_JOB_ID"

        poller = PollingEngine.from_profile(
            client      = self.client,
            environment = self.environment,
            profile     = self.profile,
            page_key    = self.PAGE_KEY
        )

        status, poll_ms = poller.poll_download_placeholder(job_id)
        elapsed_ms      = (time.monotonic() - start) * 1000

        logger.info(f"✅  [{self.PAGE_KEY}] Download complete — "
              f"elapsed: {elapsed_ms:.0f}ms")