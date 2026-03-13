import threading
from datetime import datetime
from pathlib import Path
from locust import HttpUser, task, between
from api.upload_api import UploadAPI
from utils.profile_loader import load_all_profiles, load_study_config
import time

BASE_DIR = Path(__file__).parent.parent

# ── Thread-safe global counters ────────────────────────────────────────────
_study_id_lock    = threading.Lock()
_study_id_counter = 0
_completed_lock   = threading.Lock()
_completed_count  = 0


'''def get_task_count() -> int:
    return len([
        m for m in dir(UploadFile)
        if callable(getattr(UploadFile, m))
        and hasattr(getattr(UploadFile, m), "locust_task_weight")
    ])'''


class UploadFile(HttpUser):
    wait_time = between(1, 3)
    host      = "https://postman-echo.com"

    def on_start(self):
        global _study_id_counter

        all_profiles = load_all_profiles()      #["profile1.yml","profile2.yml"]
        studies      = load_study_config()      #[{"study_id": 1}, {"study_id": 2}, ...]
        print("Studies {}".format(studies))
        print("Profiles {}".format(all_profiles))

        with _study_id_lock:
            user_index        = _study_id_counter
            _study_id_counter += 1

        profile_index   = user_index % len(all_profiles)        #If 3rd user is executed, 3 % 2 = 1
        self.profile    = all_profiles[profile_index]           # profile2.yml gets picked
        self.user_index = user_index
        self.task_done  = False

        if user_index < len(studies):
            self.study_id = studies[user_index]["study_id"]
            print(f"✅  User {user_index + 1} → "
                  f"Profile: {self.profile['profile_name']} | "
                  f"Study ID: {self.study_id}")
        else:
            self.study_id = None
            print(f"⚠️   User {user_index + 1} — Insufficient study IDs")

        print("**********************")
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] User Check on start stage {user_index + 1} ")

        print("**********************")

    @task(1)
    def upload_task(self):
        # ── Skip if already executed once ─────────────────────────────────

        print("********************")
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] User task started {self.user_index + 1}")
        if self.task_done:
            return

        self.task_done = True

        if self.study_id is None:
            print(f"⚠️   Skipping — "
                  f"Profile: {self.profile['profile_name']} — "
                  f"Insufficient study IDs")
            self._mark_complete()
            return

        file_path = (
            BASE_DIR
            / "test_data"
            / self.profile["data_template_file"]
        )

        api = UploadAPI(self.client)
        api.upload_file(
            self.study_id,
            file_path,
            self.profile["profile_name"]
        )

        print(f"📤  upload_task executed — "
              f"Study ID: {self.study_id} | "
              f"Profile: {self.profile['profile_name']}")

        self._mark_complete()

    def _mark_complete(self):
        global _completed_count

        with _completed_lock:
            _completed_count += 1
            target = self.environment.runner.target_user_count
            print(f"📊  Completed: {_completed_count}/{target}")

            if _completed_count >= target:
                print("✅  All users completed — stopping Locust")

                def quit_after_flush():
                    time.sleep(2)  # ← wait 2s for CSV to flush
                    self.environment.runner.quit()

                threading.Thread(target=quit_after_flush).start()

            print("********************")
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] User task Completed {self.user_index + 1}")
            print("********************")
