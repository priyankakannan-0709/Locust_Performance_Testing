class AuthAPI:
    complexity = "medium"

    def __init__(self, client):
        self.client = client

    def login(self, username, password):

        response = self.client.post(
            "/auth/login",
            json={
                "username": username,
                "password": password
            },
            catch_response=True
        )
        return response