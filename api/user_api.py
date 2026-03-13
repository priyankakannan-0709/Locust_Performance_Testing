class UserAPI:

    complexity = "small"

    def __init__(self, client, token):
        self.client = client
        self.token = token

    def get_profile(self):

        return self.client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {self.token}"
            },
            catch_response=True
        )

    def get_users(self):
        return self.client.get(
            "/users",
            catch_response=True
        )
