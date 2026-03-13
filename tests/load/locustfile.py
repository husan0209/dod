import uuid

from locust import HttpUser, task, between

class DODUser(HttpUser):
    """
    Нагрузочное тестирование DOD.
    Имитация реальных пользователей.
    """
    wait_time = between(1, 5)

    def on_start(self):
        """Логин перед тестами."""
        self.user_id = uuid.uuid4().hex
        self.client.post('/accounts/login/', {
            'email': f'loadtest_{self.user_id}@test.com',
            'password': 'TestPassword123!',
        })

    @task(10)
    def view_home(self):
        self.client.get('/')

    @task(8)
    def view_sports(self):
        self.client.get('/sports/')

    @task(5)
    def view_match(self):
        self.client.get('/sports/event/<test_event_id>/')

    @task(3)
    def place_bet(self):
        self.client.post('/sports/bet/', json={
            'outcome_id': '<test_outcome_id>',
            'amount': '10.00',
        })

    @task(7)
    def view_casino(self):
        self.client.get('/casino/')

    @task(5)
    def view_predictions(self):
        self.client.get('/predictions/')

    @task(4)
    def view_wallet(self):
        self.client.get('/wallet/')

    @task(2)
    def view_profile(self):
        self.client.get('/profile/')
