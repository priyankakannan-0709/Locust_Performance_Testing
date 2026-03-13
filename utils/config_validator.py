import sys
from pathlib import Path

#from tasks.upload_behavior import get_task_count
from utils.profile_loader import load_study_config
from utils.logger import get_logger
logger = get_logger(__name__)

BASE_DIR = Path(__file__).parent.parent

def validate_study_pool(user_count: int, profiles: list) -> None:
    """
        Validation 2 — Study ID pool sufficiency.
        Warns if available study IDs are insufficient for
        user_count. Never hard stops.
        len(studies) >= user_count
        Warns if user_count not evenly divisible by profile count.
        Args:
            user_count: Number of users passed via --users CLI arg
            profiles: List of profile configs loaded from load_all_profiles()
        """

    studies         = load_study_config()
    required_slots = user_count
    available       = len(studies)

    logger.info(f"🔍  Validating study ID pool...")
    logger.info(f"   Users requested : {user_count}")
    logger.info(f"   Slots required  : {required_slots}")
    logger.info(f"   Slots available : {available}")

    if required_slots > available:
        logger.warning(f"""
⚠️   WARNING: {user_count} users  =
    {required_slots} study ID slots required,
    but only {available} available in study_config.yml.
    Users beyond capacity will have their tasks skipped.
        """)
    else:
        logger.info(f"✅  Study ID pool sufficient: "
              f"{available} available, {required_slots} required\n")

    if len(profiles) > 0 and user_count % len(profiles) != 0:
        logger.warning(f"⚠️   Warning: {user_count} users not evenly divisible "
              f"by {len(profiles)} profiles\n"
              f"   Recommended: use a multiple of {len(profiles)} "
              f"for --users flag")
    else:
        logger.info(f"✅  User count {user_count} evenly distributes "
              f"across {len(profiles)} profiles — "
              f"{user_count // len(profiles)} users per profile\n")


def validate_test_data_files(profiles: list) -> None:
    """
    Validates data files exist on the folder
    config file validation already done by load_all_profiles(). - profile loader
    """
    test_data_dir = BASE_DIR / "config" / "profile_test_data"

    logger.info("\n🔍  Validating profile configs...")

    for profile in profiles:
        profile_name = profile["profile_name"]

        for page_key, page_config in profile["page_data"].items():

            if page_config is None or "data_file" not in page_config:
                continue   # no file for this page — skip

            data_file = page_config["data_file"]
            full_path = test_data_dir / data_file

            if not full_path.exists():
                logger.error(f"❌  {profile_name} → {page_key} → "
                      f"{data_file} not found at {full_path}")
                sys.exit(1)

            logger.info(f"✅  {profile_name} → {page_key} → {data_file} found")

    logger.info(f"\n✅  All {len(profiles)} profile configs valid\n")

def validate_stress_config() -> None:
    """
    Validates stress_config.yml exists and has required fields.
    Hard stop if missing.
    Stub — full implementation pending stress mode development.
    """
    import yaml

    stress_config_path = BASE_DIR / "config" / "stress_config" / "stress_config.yml"

    logger.info("\n🔍  Validating stress config...")

    # ── Check file exists ──────────────────────────────────────────────────
    if not stress_config_path.exists():
        logger.error(f"❌  stress_config.yml not found at {stress_config_path} — "
              f"cannot proceed")
        sys.exit(1)

    # ── Check required fields ──────────────────────────────────────────────
    with open(stress_config_path, "r") as f:
        stress_config = yaml.safe_load(f)

    if not stress_config:
        logger.error(f"❌  stress_config.yml is empty — cannot proceed")
        sys.exit(1)

    if "target_apis" not in stress_config:
        logger.error(f"❌  stress_config.yml missing target_apis field — "
              f"cannot proceed")
        sys.exit(1)

    if not stress_config["target_apis"]:
        logger.error(f"❌  stress_config.yml target_apis is empty — "
              f"add at least one API to target")
        sys.exit(1)

    logger.info(f"✅  stress_config.yml found")
    logger.info(f"✅  target_apis: "
          f"{[api['endpoint'] for api in stress_config['target_apis']]}\n")

    # ── STUB — additional stress validation pending ────────────────────────
    # TODO: validate concurrency_steps present
    # TODO: validate thresholds present
    # TODO: validate profile files exist for stress mode

def validate_for_mode(mode: str, user_count: int, profiles: list) -> None:
    """
    Routes to correct validation functions based on mode.
    Single entry point for all pre-flight validation.

    Args:
        mode       : "journey" or "stress"
        user_count : number of users from --users CLI arg
        profiles   : profiles loaded by load_all_profiles()
    """

    if mode == "journey":
        validate_test_data_files(profiles)
        validate_study_pool(user_count, profiles)

    elif mode == "stress":
        validate_stress_config()

    else:
        logger.error(f"❌  Unknown mode: '{mode}' — "
              f"must be 'journey' or 'stress'")
        sys.exit(1)