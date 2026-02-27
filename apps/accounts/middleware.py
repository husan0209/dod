from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from user_agents import parse as parse_ua

from .models import ActiveSession


class LastActivityMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated:
            request.user.last_activity = timezone.now()
            request.user.is_online = True
            request.user.save(update_fields=["last_activity", "is_online", "updated_at"])
        return None


class DeviceTrackingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        session_key = request.session.session_key
        if not session_key:
            return None

        ua_string = request.META.get("HTTP_USER_AGENT", "")
        ua = parse_ua(ua_string) if ua_string else None
        device_type = "desktop"
        if ua:
            if ua.is_mobile:
                device_type = "mobile"
            elif ua.is_tablet:
                device_type = "tablet"
            elif ua.is_pc:
                device_type = "desktop"
            else:
                device_type = "unknown"
        defaults = {
            "ip_address": request.META.get("REMOTE_ADDR"),
            "device_type": device_type,
            "browser": f"{ua.browser.family} {ua.browser.version_string}" if ua else "",
            "os": f"{ua.os.family} {ua.os.version_string}" if ua else "",
            "device_name": ua.device.family if ua else "",
        }
        ActiveSession.objects.update_or_create(
            session_key=session_key,
            defaults={**defaults, "user": request.user, "is_current": True},
        )
        return None
