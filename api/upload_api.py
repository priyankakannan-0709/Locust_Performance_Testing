from pathlib import Path
from utils.logger import get_logger
logger = get_logger(__name__)
BASE_DIR = Path(__file__).parent

class UploadAPI:
    complexity = "complex"

    def __init__(self, client):
        self.client = client
        self.headers = {}

    def upload_file(self, study_id, file_path, profile_name):
        """
                        Upload a file to postman echo endpoint as multipart form data.

                        Args:
                            study_id: Study ID assigned to this task (printed for verification)
                            file_path: Full path to the file to upload
        """
        logger.info(f"DEBUG — upload_file called")
        logger.info(f"DEBUG — client: {self.client}")
        logger.info(f"DEBUG — client base_url: {self.client.base_url}")
        logger.info("Printing information from API file")
        logger.info(f"📤  Uploading — Study ID: {study_id} | "
              f"Profile: {profile_name} | File: {file_path.name}")
        with open(file_path, "rb") as f:
            logger.info(f"DEBUG — file opened successfully")
            files = {
                "file": (
                    file_path.name,
                    f,
                    "application/octet-stream"
                )
            }

            with self.client.post(
                "https://postman-echo.com/post",   # for httpbin testing
                name=f"POST /upload/{profile_name}",
                headers=self.headers,
                files=files,
                catch_response=True
            ) as response:
                logger.info(f"DEBUG — response received: {response.status_code}")

        return response