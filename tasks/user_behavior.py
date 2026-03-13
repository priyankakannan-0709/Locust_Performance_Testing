from locust import TaskSet, task, tag, SequentialTaskSet
from api.auth_api import AuthAPI
from api.user_api import UserAPI
from utils.data_loader import  load_users, get_random_user

class UserBehavior(SequentialTaskSet):

    users_data = load_users("test_data/users.csv")

    def on_start(self):
        print("on_start")

        self.auth_api = AuthAPI(self.client)

        user = get_random_user(self.users_data)
        print(user)

        response = self.auth_api.login(user["username"], user["password"])

        print("Login status:", response.status_code)
        print("Login response:", response.text)

        with response as res:
            if res.status_code == 200:
                data = res.json()
                #print(res.text)

                if "accessToken" in data:
                    self.access_token = data["accessToken"]
                    self.user_api = UserAPI(self.client, self.access_token)
                else:
                    res.failure("Login response missing access token")
                    self.interrupt()
            else:
                res.failure("Login failed with status {res.status_code}")



    @tag("profile")
    @task
    def get_profile_task(self):

        response = self.user_api.get_profile()

        with response as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure("Profile fetch failed")


    @task
    def get_users_task(self):
        response = self.user_api.get_users()

        with response as res:
            if res.status_code == 200:
                res.success()
            else:
                res.failure("Users fetch failed")

    '''@task
    def get_complete_task(self):
        if self.user.environment.runner.user_count == 1:
            self.user.environment.runner.quit()'''


    '''def on_stop(self):
        print("All APIs executed once. Quitting Locust.")
        # Stop the entire Locust run
        self.user.environment.runner.quit()'''