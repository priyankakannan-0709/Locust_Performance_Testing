from pathlib import Path
from utils.logger import get_logger
logger = get_logger(__name__)

class BaselineAPI:

    def __init__(self, client):
        self.client  = client
        self.headers = {}

    def upload(self, study_id, file_path, name) -> object:
        """
        Upload baseline data file to endpoint.

        Args:
            study_id  : study ID for this user session
            file_path : full path to the baseline data file
            name      : Locust name= parameter for reporting

        Returns:
            response object
        """
        logger.info(f"📤  BaselineAPI.upload — "
              f"Study ID: {study_id} | "
              f"File: {file_path.name}")

        with open(file_path, "rb") as f:
            files = {
                "file": (
                    file_path.name,
                    f,
                    "application/octet-stream"
                )
            }

            with self.client.post(
                "/post",                  # dummy: postman echo
                name           = name,
                headers        = self.headers,
                files          = files,
                catch_response = True
            ) as response:
                logger.info(f"📤  BaselineAPI.upload — "
                      f"status: {response.status_code}")

        return response

    def download(self, study_id, name) -> object:
        """
        Trigger baseline download for given study ID.

        Args:
            study_id : study ID to download baseline for
            name     : Locust name= parameter for reporting

        Returns:
            response object
        """
        logger.info(f"📥  BaselineAPI.download — "
              f"Study ID: {study_id}")

        with self.client.get(
            f"/get?study_id={study_id}",   # dummy: postman echo
            name           = name,
            headers        = self.headers,
            catch_response = True
        ) as response:
            logger.info(f"📥  BaselineAPI.download — "
                  f"status: {response.status_code}")

        return response