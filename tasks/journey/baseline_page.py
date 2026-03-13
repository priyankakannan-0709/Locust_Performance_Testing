import time
from tasks.journey.base_page  import BasePage
from api.baseline_api         import BaselineAPI
from utils.polling_engine     import PollingEngine, STATUS_COMPLETED
from utils.logger import get_logger
logger = get_logger(__name__)

class BaselinePage(BasePage):
    """
    Page 2 — Baseline
    Operations: upload + download
    Both operations trigger async artifact jobs — polled until complete.
    """

    PAGE_KEY = "baseline_page"

    def __init__(self, client, environment, profile, study_id):
        super().__init__(client, environment, profile, study_id)
        self.api = BaselineAPI(self.client)              # ← instantiate once

    def execute(self):
        page_start = time.monotonic()

        self._execute_upload()
        self._execute_download()

        self._fire_page_event(
            elapsed_ms = (time.monotonic() - page_start) * 1000
        )

    def _execute_upload(self):
        start     = time.monotonic()
        file_path = self._get_data_file_path()

        logger.info(f"📤  [{self.PAGE_KEY}][{self.profile['profile_name']}] "
              f"Uploading: {file_path.name}")

        response = self.api.upload(
            study_id  = self.study_id,
            file_path = file_path,
            name      = self._name("POST", "/api/baseline/upload")
        )

        if response.status_code != 200:
            logger.warning(f"❌  [{self.PAGE_KEY}] Upload failed: "
                  f"{response.status_code}")
            return

        # ── STUB — extract job_id from response ────────────────────────────
        # Real implementation:
        #   job_id = response.json()["job_id"]
        job_id = "STUB_UPLOAD_JOB_ID"

        poller = PollingEngine.from_profile(
            client      = self.client,
            environment = self.environment,
            profile     = self.profile,
            page_key    = self.PAGE_KEY
        )

        status, poll_ms = poller.poll_until_complete(job_id)
        elapsed_ms      = (time.monotonic() - start) * 1000

        if status != STATUS_COMPLETED:
            logger.info(f"❌  [{self.PAGE_KEY}] Upload job {status} — "
                  f"elapsed: {elapsed_ms:.0f}ms")
        else:
            logger.info(f"✅  [{self.PAGE_KEY}] Upload complete — "
                  f"elapsed: {elapsed_ms:.0f}ms")

    def _execute_download(self):
        start = time.monotonic()

        logger.info(f"📥  [{self.PAGE_KEY}][{self.profile['profile_name']}] "
              f"Downloading for study_id: {self.study_id}")

        response = self.api.download(
            study_id = self.study_id,
            name     = self._name("GET", "/api/baseline/download/{study_id}")
        )

        if response.status_code != 200:
            logger.info(f"❌  [{self.PAGE_KEY}] Download failed: "
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