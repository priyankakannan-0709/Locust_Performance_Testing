import time
from utils.logger import get_logger
logger = get_logger(__name__)
from pathlib import Path


# ── Poll status constants ──────────────────────────────────────────────────
STATUS_COMPLETED = "completed"
STATUS_FAILED    = "failed"
STATUS_TIMEOUT   = "timeout"
STATUS_STUCK     = "stuck"
STATUS_ERROR     = "error"


class PollingEngine:
    """
    Handles async job polling for upload and download operations.

    Two configurable thresholds per page per profile:
        expected_ms  : warn if job exceeds this duration
        max_wait_ms  : fail immediately if job exceeds this duration

    Both thresholds are read from profile YAML:
        page_data:
            data_prep_page:
                polling:
                    interval_seconds : 10
                    expected_ms      : 120000   # 2 min — warn threshold
                    max_wait_ms      : 300000   # 5 min — fail threshold
    """

    def __init__(
        self,
        client,
        environment,
        page_key:          str,
        profile_name:      str,
        interval_seconds:  int,
        expected_ms:       int,
        max_wait_ms:       int
    ):
        self.client           = client
        self.environment      = environment
        self.page_key         = page_key
        self.profile_name     = profile_name
        self.interval_seconds = interval_seconds
        self.expected_ms      = expected_ms
        self.max_wait_ms      = max_wait_ms

    # ── Factory method — build from profile page_data ──────────────────────
    @classmethod
    def from_profile(cls, client, environment, profile: dict, page_key: str):
        """
        Build PollingEngine from profile YAML page_data block.

        Reads polling config from:
            profile["page_data"][page_key]["polling"]

        Args:
            client      : Locust HttpSession client
            environment : Locust environment
            profile     : full profile dict loaded from YAML
            page_key    : page key e.g. "data_prep_page"

        Returns:
            PollingEngine instance configured for this page + profile
        """
        page_data      = profile["page_data"].get(page_key, {})
        polling_config = page_data.get("polling", {})

        if not polling_config:
            raise ValueError(
                f"No polling config found for page '{page_key}' "
                f"in profile '{profile['profile_name']}'\n"
                f"Add polling block to profile YAML:\n"
                f"  {page_key}:\n"
                f"    polling:\n"
                f"      interval_seconds: 10\n"
                f"      expected_ms: 120000\n"
                f"      max_wait_ms: 300000"
            )

        return cls(
            client           = client,
            environment      = environment,
            page_key         = page_key,
            profile_name     = profile["profile_name"],
            interval_seconds = polling_config.get("interval_seconds", 10),
            expected_ms      = polling_config.get("expected_ms",      120000),
            max_wait_ms      = polling_config.get("max_wait_ms",      300000),
        )

    # ── Main polling method ────────────────────────────────────────────────
    def poll_until_complete(self, job_id: str) -> tuple:
        """
        Poll job status until terminal state or threshold exceeded.

        Thresholds:
            expected_ms : log warning if job exceeds this
            max_wait_ms : fail immediately if job exceeds this

        Args:
            job_id: job ID returned from upload or download trigger

        Returns:
            tuple: (final_status, elapsed_ms)
                final_status: one of STATUS_* constants
                elapsed_ms  : total time spent polling
        """
        start_ms          = time.monotonic() * 1000
        warning_logged    = False
        attempt           = 0

        logger.info(f"⏳  [{self.page_key}][{self.profile_name}] "
              f"Polling job: {job_id} | "
              f"expected: {self.expected_ms}ms | "
              f"max_wait: {self.max_wait_ms}ms")

        while True:
            elapsed_ms = (time.monotonic() * 1000) - start_ms

            # ── Check max_wait_ms — fail immediately ───────────────────────
            if elapsed_ms >= self.max_wait_ms:
                logger.error(f"❌  [{self.page_key}][{self.profile_name}] "
                      f"Job {job_id} TIMEOUT — "
                      f"exceeded max_wait {self.max_wait_ms}ms "
                      f"after {elapsed_ms:.0f}ms")
                return STATUS_TIMEOUT, elapsed_ms

            # ── Check expected_ms — warn once ──────────────────────────────
            if elapsed_ms >= self.expected_ms and not warning_logged:
                logger.warning(f"⚠️   [{self.page_key}][{self.profile_name}] "
                      f"Job {job_id} running longer than expected — "
                      f"expected: {self.expected_ms}ms | "
                      f"elapsed: {elapsed_ms:.0f}ms | "
                      f"still polling until {self.max_wait_ms}ms")
                warning_logged = True

            # ── Poll job status ────────────────────────────────────────────
            status, elapsed_ms = self._poll_once(job_id, elapsed_ms)

            attempt += 1
            logger.info(f"🔄  [{self.page_key}][{self.profile_name}] "
                  f"Attempt {attempt} | "
                  f"job: {job_id} | "
                  f"status: {status} | "
                  f"elapsed: {elapsed_ms:.0f}ms")

            # ── Terminal states — return immediately ───────────────────────
            if status == STATUS_COMPLETED:
                logger.info(f"✅  [{self.page_key}][{self.profile_name}] "
                      f"Job {job_id} completed in {elapsed_ms:.0f}ms")
                return STATUS_COMPLETED, elapsed_ms

            if status == STATUS_FAILED:
                logger.info(f"❌  [{self.page_key}][{self.profile_name}] "
                      f"Job {job_id} FAILED after {elapsed_ms:.0f}ms")
                return STATUS_FAILED, elapsed_ms

            if status == STATUS_ERROR:
                logger.error(f"❌  [{self.page_key}][{self.profile_name}] "
                      f"Job {job_id} ERROR after {elapsed_ms:.0f}ms")
                return STATUS_ERROR, elapsed_ms

            # ── Wait before next poll ──────────────────────────────────────
            time.sleep(self.interval_seconds)

    # ── Single poll attempt ────────────────────────────────────────────────
    def _poll_once(self, job_id: str, elapsed_ms: float) -> tuple:
        """
        Make one poll request to check job status.

        STUB — real implementation requires:
            - actual poll endpoint URL
            - actual response structure
            - actual status field name and values

        Args:
            job_id    : job ID to poll
            elapsed_ms: current elapsed time (for logging)

        Returns:
            tuple: (status, elapsed_ms)
        """
        # ── STUB — replace with real implementation ────────────────────────
        # Example of what real implementation will look like:
        #
        # with self.client.get(
        #     f"/api/jobs/{job_id}",
        #     name  = f"[POLL][{self.page_key}] GET /api/jobs/{{job_id}}",
        #     catch_response = True
        # ) as response:
        #     if response.status_code != 200:
        #         response.failure(f"Poll failed: {response.status_code}")
        #         return STATUS_ERROR, elapsed_ms
        #
        #     response.success()   # always mark success — polls not tracked
        #
        #     data   = response.json()
        #     status = data.get("status")   # ← real field name TBD
        #
        #     if status == "completed":     # ← real status value TBD
        #         return STATUS_COMPLETED, elapsed_ms
        #     if status == "failed":        # ← real status value TBD
        #         return STATUS_FAILED, elapsed_ms
        #     return status, elapsed_ms     # ← running/pending etc

        logger.info(f"🔧  STUB — _poll_once() not yet implemented | "
              f"job_id: {job_id}")
        return STATUS_COMPLETED, elapsed_ms   # ← stub returns completed

    # ── Download polling placeholder ───────────────────────────────────────
    def poll_download_placeholder(self, job_id: str) -> tuple:
        """
        Placeholder for download job polling.
        Real implementation pending — requires download API details.

        Args:
            job_id: job ID returned from download trigger

        Returns:
            tuple: (STATUS_COMPLETED, 0.0) — stub always succeeds
        """
        # ── STUB — replace with real implementation ────────────────────────
        # Download polling follows same pattern as poll_until_complete()
        # but may have different:
        #   - poll endpoint URL
        #   - response structure
        #   - status field name and values
        #   - completion criteria

        logger.info(f"⏳  STUB — download polling not yet implemented | "
              f"job_id: {job_id} | "
              f"page: {self.page_key} | "
              f"profile: {self.profile_name}")
        return STATUS_COMPLETED, 0.0