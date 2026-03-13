from utils.logger import get_logger
logger = get_logger(__name__)

class StudyDetailsAPI:

    def __init__(self, client):
        self.client  = client
        self.headers = {}

    def get_details(self, study_id, name) -> object:
        """
        Fetch study details for given study ID.

        Args:
            study_id : study ID to fetch details for
            name     : Locust name= parameter for reporting

        Returns:
            response object
        """
        logger.info(f"📋  StudyDetailsAPI.get_details — "
              f"Study ID: {study_id}")

        with self.client.get(
            f"/get?study_id={study_id}",   # dummy: postman echo
            name           = name,
            headers        = self.headers,
            catch_response = True
        ) as response:
            logger.info(f"📋  StudyDetailsAPI.get_details — "
                  f"status: {response.status_code}")

        return response

    def get_summary(self, study_id, name) -> object:
        """
        Fetch study summary for given study ID.

        Args:
            study_id : study ID to fetch summary for
            name     : Locust name= parameter for reporting

        Returns:
            response object
        """
        logger.info(f"📋  StudyDetailsAPI.get_summary — "
              f"Study ID: {study_id}")

        with self.client.get(
            f"/get?study_id={study_id}&type=summary",   # dummy: postman echo
            name           = name,
            headers        = self.headers,
            catch_response = True
        ) as response:
            logger.info(f"📋  StudyDetailsAPI.get_summary — "
                  f"status: {response.status_code}")

        return response