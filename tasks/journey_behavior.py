import os
import threading
import time
from pathlib import Path

from locust import HttpUser, task, between

from tasks.journey.data_prep_page     import DataPrepPage
from tasks.journey.baseline_page      import BaselinePage
from tasks.journey.scoping_page       import ScopingPage
from tasks.journey.study_details_page import StudyDetailsPage
from utils.profile_loader             import load_all_profiles, load_study_config
from utils.logger import get_logger
logger = get_logger(__name__)

# ── Module-level thread-safe counters ─────────────────────────────────────
# Shared across all user threads — must be protected by locks

_study_id_lock    = threading.Lock()
_study_id_counter = 0   # increments once per user spawned

_completed_lock  = threading.Lock()
_completed_count = 0    # increments once per user that finishes journey


class JourneyUser(HttpUser):
    """
    Simulates a real user journey across all 4 pages sequentially.

    Each user is assigned:
        - One profile (round-robin by row_count ascending)
        - One study ID (from study_config.yml)

    All users run in parallel — each user's pages run sequentially.
    """

    host      = os.getenv("TARGET_HOST", "https://postman-echo.com")
    wait_time = between(1, 3)

    def on_start(self):
        """
        Called once per user when it spawns.
        Assigns profile and study ID using thread-safe round-robin.
        """
        global _study_id_counter

        all_profiles = load_all_profiles()   # sorted by row_count ascending
        studies      = load_study_config()

        # ── Assign unique user index — thread safe ─────────────────────────
        with _study_id_lock:
            user_index        = _study_id_counter
            _study_id_counter += 1

        # ── Assign profile via round-robin ─────────────────────────────────
        # user 0 → profile 0 (smallest)
        # user 1 → profile 1
        # user N → profile N % len(profiles) (wraps)
        profile_index  = user_index % len(all_profiles)
        self.profile   = all_profiles[profile_index]
        self.task_done = False

        # ── Assign study ID ────────────────────────────────────────────────
        if user_index < len(studies):
            self.study_id = studies[user_index]["study_id"]
        else:
            self.study_id = None
            logger.warning(f"⚠️   User {user_index + 1} has no study ID — "
                  f"journey will be skipped")

        logger.info(f"✅  User {user_index + 1} assigned → "
              f"Profile: {self.profile['profile_name']} | "
              f"Rows: {self.profile['row_count']} | "
              f"Study ID: {self.study_id}")

    @task
    def run_full_journey(self):
        """
        Executes all 4 pages sequentially for this user.
        Guard ensures this runs exactly once per user.
        """
        # ── Guard — run once only per user ─────────────────────────────────
        if self.task_done:
            return

        self.task_done = True

        # ── Skip if no study ID assigned ───────────────────────────────────
        if self.study_id is None:
            logger.warning(f"⏭️   Skipping journey — no study ID assigned")
            self._mark_complete()
            return

        logger.info(f"\n🚀  Starting journey → "
              f"Profile: {self.profile['profile_name']} | "
              f"Study ID: {self.study_id}\n")

        journey_start = time.monotonic()


        # ── Page 1 — Study Details ─────────────────────────────────────────
        logger.info(f"📄  Page 1/4 — Study Details")
        StudyDetailsPage(
            client      = self.client,
            environment = self.environment,
            profile     = self.profile,
            study_id    = self.study_id
        ).execute()

        # ── Page 2 — Scoping ───────────────────────────────────────────────
        logger.info(f"📄  Page 2/4 — Scoping")
        ScopingPage(
            client      = self.client,
            environment = self.environment,
            profile     = self.profile,
            study_id    = self.study_id
        ).execute()

        # ── Page 3 — Data Preparation ──────────────────────────────────────
        logger.info(f"📄  Page 3/4 — Data Prep")
        DataPrepPage(
            client      = self.client,
            environment = self.environment,
            profile     = self.profile,
            study_id    = self.study_id
        ).execute()

        # ── Page 4 — Baseline ──────────────────────────────────────────────
        logger.info(f"📄  Page 4/4 — Baseline")
        BaselinePage(
            client      = self.client,
            environment = self.environment,
            profile     = self.profile,
            study_id    = self.study_id
        ).execute()

        journey_ms = (time.monotonic() - journey_start) * 1000

        logger.info(f"\n🏁  Journey complete → "
              f"Profile: {self.profile['profile_name']} | "
              f"Study ID: {self.study_id} | "
              f"Total: {journey_ms:.0f}ms\n")

        self._mark_complete()

    def _mark_complete(self):
        """
        Thread-safe completion counter.
        When all users finish, waits 2s for CSV flush then quits.
        """
        global _completed_count

        with _completed_lock:
            _completed_count += 1
            total_users  = self.environment.runner.target_user_count
            current      = _completed_count

        logger.info(f"🔢  Completed: {current}/{total_users}")

        if current >= total_users:
            logger.info(f"✅  All {total_users} users completed — "
                  f"waiting for CSV flush before exit...")

            def quit_after_flush():
                time.sleep(2)   # wait for Locust CSV writer to flush
                logger.info(f"👋  Shutting down Locust...")
                self.environment.runner.quit()

            threading.Thread(
                target = quit_after_flush,
                daemon = True
            ).start()
