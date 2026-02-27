from config import celery_app  # pragma: no cover


@celery_app.task(name="accounts.send_email_verification")
def send_email_verification(email: str, token: str):
    # TODO: implement real email sending
    pass
