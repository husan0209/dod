import sys
import os
import traceback
import django

def log(msg):
    # Print to stdout as well so we can see it in terminal if it's not truncated
    print(msg)
    with open('import_log.txt', 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

if os.path.exists('import_log.txt'):
    os.remove('import_log.txt')

log("Starting import test with Django setup...")

# Set project root to PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
try:
    django.setup()
    log("SUCCESS: Django setup complete.")
except Exception as e:
    log(f"FAILURE: Django setup failed. Error: {e}")
    log(traceback.format_exc())
    sys.exit(1)

try:
    log("Attempting to import apps.accounts.models...")
    from apps.accounts import models
    log("SUCCESS: apps.accounts.models imported.")
    
    log("Attempting to import Notification from apps.accounts.models...")
    from apps.accounts.models import Notification
    log("SUCCESS: Notification imported.")

    log("Attempting to import apps.accounts.services.notification_service...")
    from apps.accounts.services import notification_service
    log("SUCCESS: notification_service module imported.")

    log("Attempting to import apps.accounts.services.otp_service...")
    from apps.accounts.services import otp_service
    log("SUCCESS: otp_service module imported.")
    
    log("Importing OTPService...")
    from apps.accounts.services.otp_service import OTPService
    log(f"SUCCESS: OTPService class found: {OTPService}")

except Exception as e:
    log(f"FAILURE during imports: {e}")
    log(traceback.format_exc())

log("Test finished.")
