import time
from pathlib import Path
from locust import events

BASE_DIR = Path(__file__).parent.parent.parent

class BasePage:
    """
    Base class for all journey page classes.
    Provides shared utilities for request naming,
    page event firing and data file resolution.

    Every subclass MUST define:
        PAGE_KEY: str — matches key in profile YAML page_data block
    """

    PAGE_KEY: str = None   # ← must be overridden by every subclass

    def __init__(self, client, environment, profile, study_id):
        self.client      = client
        self.environment = environment
        self.profile     = profile
        self.study_id    = study_id

        # ── Validate PAGE_KEY defined on subclass ──────────────────────────
        if self.PAGE_KEY is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define PAGE_KEY"
            )

        # ── Load this page's config from profile ───────────────────────────
        self.page_data = profile["page_data"].get(self.PAGE_KEY, {})
        self.sla       = self.page_data.get("expected_sla", {})

    # ── Abstract method — must be implemented by every page ───────────────
    def execute(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute()"
        )

    # ── Data file resolution ───────────────────────────────────────────────
    def _get_data_file_path(self) -> Path:
        """
        Resolve full path to this page's test data file.
        Reads data_file from page_data block in profile.

        Returns:
            Path: full resolved path to the data file

        Raises:
            ValueError: if data_file not defined for this page
        """
        if "data_file" not in self.page_data:
            raise ValueError(
                f"{self.__class__.__name__} has no data_file defined "
                f"in profile '{self.profile['profile_name']}' "
                f"under page_key '{self.PAGE_KEY}'"
            )

        data_file = self.page_data["data_file"]
        full_path = BASE_DIR / "config" / "profile_test_data" / data_file

        if not full_path.exists():
            raise FileNotFoundError(
                f"Test data file not found: {full_path}\n"
                f"Profile : {self.profile['profile_name']}\n"
                f"Page    : {self.PAGE_KEY}\n"
                f"File    : {data_file}"
            )

        return full_path

    # ── Page event firing ──────────────────────────────────────────────────
    def _fire_page_event(
        self,
        elapsed_ms: float,
        exception=None
    ) -> None:
        """
        Fire a PAGE-level custom Locust event.
        Appears in CSV and reports as a PAGE row.

        Args:
            operation : "upload", "download", or "page_load"
            elapsed_ms: total wall-clock time for this operation
            exception : Exception if operation failed, None if success
        """
        self.environment.events.request.fire(
            request_type    = "PAGE",
            name            = (
                f"[{self.PAGE_KEY}]"
                f"[{self.profile['profile_name']}]"
            ),
            response_time   = elapsed_ms,
            response_length = 0,
            exception       = exception,
            context         = {}
        )

    # ── Locust name parameter helper ───────────────────────────────────────
    def _name(self, method: str, endpoint: str) -> str:
        """
        Build consistent Locust name parameter for all requests.
        Used as name= in every self.client call.

        Args:
            method  : HTTP method e.g. "GET", "POST", "PUT"
            endpoint: endpoint path e.g. "/api/study/details"

        Returns:
            str: formatted name string

        Example:
            self._name("POST", "/api/data-prep/upload")
            → "[data_prep_page][profile_50_rows] POST /api/data-prep/upload"
        """
        return (
            f"[{self.PAGE_KEY}]"
            f"[{self.profile['profile_name']}] "
            f"{method} {endpoint}"
        )