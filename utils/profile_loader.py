import sys

import yaml
from pathlib import Path
from utils.logger import get_logger
logger = get_logger(__name__)

BASE_DIR = Path(__file__).parent.parent  # points to framework root


def load_all_profiles() -> list:
    """
    Load all profile configs from config/profile_config/.
    Validates page_data exists in every profile.
    Returns profiles sorted by row_count ascending.

    Returns:
        list: Sorted list of profile
              ['profile_50_rows', 'profile_100_rows']
    """
    profile_dir = BASE_DIR / "config" / "profile_config"

    if not profile_dir.exists():
        raise FileNotFoundError(
            f"❌  Profile config directory not found: {profile_dir}"
        )

    # Get the list of profile yml files from the directory
    profile_files = [
        f for f in profile_dir.iterdir()
        if f.suffix == ".yml"
           and not f.name.startswith(".")
    ]

    if not profile_files:
        raise FileNotFoundError(
            f"❌  No .yml profile configs found in: {profile_dir}"
        )

    profiles = []
    for profile_file in profile_files:
        try:
            with open(profile_file, "r") as f:
                profile = yaml.safe_load(f)

                if "profile_name" not in profile:
                    logger.error(f"❌  {profile_file.name} missing profile_name — "
                          f"cannot proceed")
                    sys.exit(1)

                if "row_count" not in profile:
                    logger.error(f"❌  {profile_file.name} missing row_count field")
                    sys.exit(1)

                if not isinstance(profile["row_count"], int) \
                        or profile["row_count"] <= 0:
                    logger.error(f"❌  {profile_file.name} row_count must be "
                          f"an integer greater than 0")
                    sys.exit(1)

                if "page_data" not in profile:
                    logger.error(f"❌  {profile_file.name} missing page_data block — "
                          f"cannot proceed")
                    sys.exit(1)

                if not isinstance(profile["page_data"], dict) \
                        or len(profile["page_data"]) == 0:
                    logger.error(f"❌  {profile_file.name} page_data is empty — "
                          f"at least one page must be defined")
                    sys.exit(1)

                profiles.append(profile)

                logger.info(f"✅  Loaded profile config: {profile_file.name}")

        except Exception as e:
            raise RuntimeError(
                f"❌  Failed to load profile config {profile_file.name}: {e}"
            )
     # User 1 → smallest, User 2 → next, ..., wraps back to smallest
    profiles.sort(key=lambda p: p["row_count"]) #output would be [profile_50_rows,  profile_100_rows, profile_150_rows ,...]

    logger.info(f"📋  Total profiles loaded: {len(profiles)}")
    logger.info(f"📋  Profiles loaded in order: "
          f"{[p['profile_name'] for p in profiles]}")

    return profiles


def load_study_config() -> list:
    """
    Load config/study_config/study_config.yml and return
    the list of studies.

    Returns:
        list: List of study dicts
              e.g. [{"study_id": 1}, {"study_id": 2}, ...]
    """
    study_config_path = BASE_DIR / "config" / "study_config.yml"

    if not study_config_path.exists():
        raise FileNotFoundError(
            f"❌  Study config not found: {study_config_path}"
        )

    try:
        with open(study_config_path, "r") as f:
            config = yaml.safe_load(f)

        studies = config.get("studies")

        if not studies:
            raise ValueError(
                f"❌  No 'studies' key found in {study_config_path}"
            )

        logger.info(f"✅  Study config loaded — {len(studies)} studies available")
        return studies

    except Exception as e:
        raise RuntimeError(
            f"❌  Failed to load study config: {e}"
        )