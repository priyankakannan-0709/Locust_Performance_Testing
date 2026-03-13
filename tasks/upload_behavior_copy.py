import threading
from pathlib import Path

from locust import SequentialTaskSet, task, between

from api.upload_api import UploadAPI
from utils.profile_loader import load_all_profiles, load_study_config

_study_id_lock    = threading.Lock()
_study_id_counter = 0
BASE_DIR = Path(__file__).parent.parent
def get_task_count() -> int:
    return len([
        m for m in dir(UploadBehavior)
        if callable(getattr(UploadBehavior, m))
        and hasattr(getattr(UploadBehavior, m), "locust_task_weight")
    ])

class UploadBehavior(SequentialTaskSet):
    wait_time = between(1, 3)

    def on_start(self):
        self.upload_api = UploadAPI(self.client)
        """
                Called once per user at spawn time.
                Loads all profiles and study config, then assigns
                unique study IDs to each task slot using strict
                global counter ordering.
                """
        global _study_id_counter

        # ── Load configs ───────────────────────────────────────────────────
        self.profiles = load_all_profiles()
        print(f"*******PROFILES,{self.profiles}")
        self.studies = load_study_config()
        task_count = get_task_count()

        # ── Assign study IDs strictly via global counter ───────────────────
        with _study_id_lock:
            base_slot = _study_id_counter
            _study_id_counter += 1

        # ── Map each task slot to a unique study ID ────────────────────────
        self.study_ids = {}

        #for i in range(task_count):
        slot = base_slot
        task_key = f"task_{1}"

        if slot < len(self.studies):
            self.study_ids[task_key] = self.studies[slot]["study_id"]
            print(f"✅  {task_key} assigned "
                      f"Study ID: {self.study_ids[task_key]}")
        else:
            self.study_ids[task_key] = None
            print(f"⚠️   {task_key} — Insufficient study IDs, "
                      f"task will be skipped")

    @task(1)
    def upload_task_1(self):
        """
        Task 1 — picks profile_1.yml and its corresponding test data file.
        Always uses self.profiles[0] and self.study_ids["task_1"].
        """
        study_id = self.study_ids.get("task_1")

        if study_id is None:
            print("⚠️   Skipping upload_task_1 — Insufficient study IDs")
            return

        profile = self.profiles[0]  # index 0 → profile_1.yml
        file_path = BASE_DIR / "test_data" / profile["data_template_file"]


        response = self.upload_api.upload_file(study_id, file_path,profile["profile_name"])

        with response as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure(f"Bad status: {res.status_code}")

        print(f"📤  Task 1 executed — "
              f"Study ID: {study_id}, "
              f"Profile: {profile['profile_name']}")

    @task(1)
    def upload_task_2(self):
        """
        Task 1 — picks profile_1.yml and its corresponding test data file.
        Always uses self.profiles[0] and self.study_ids["task_1"].
        """
        study_id = self.study_ids.get("task_2")

        if study_id is None:
            print("⚠️   Skipping upload_task_2 — Insufficient study IDs")
            return

        profile = self.profiles[1]  # index 1 → profile_2.yml
        file_path = BASE_DIR / "test_data" / profile["data_template_file"]

        response = self.upload_api.upload_file(study_id, file_path,profile["profile_name"])

        with response as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure(f"Bad status: {res.status_code}")

        print(f"📤  Task 2 executed — "
              f"Study ID: {study_id}, "
              f"Profile: {profile['profile_name']}")
