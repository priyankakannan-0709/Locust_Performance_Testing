from utils.logger import get_logger
logger = get_logger(__name__)
class ScopingAPI:

    def __init__(self, client):
        self.client  = client
        self.headers = {}

    def download(self, study_id, name) -> object:
        """
        Trigger scoping download for given study ID.

        Args:
            study_id : study ID to download scoping data for
            name     : Locust name= parameter for reporting

        Returns:
            response object
        """
        logger.info(f"📥  ScopingAPI.download — "
              f"Study ID: {study_id}")

        with self.client.get(
            f"/get?study_id={study_id}",   # dummy: postman echo
            name           = name,
            headers        = self.headers,
            catch_response = True
        ) as response:
            logger.info(f"📥  ScopingAPI.download — "
                  f"status: {response.status_code}")

        return response