from uuid import uuid4


def generate_uuid_filename(instance, filename: str, prefix: str = "") -> str:
    ext = filename.split('.')[-1]
    return f"{prefix}{uuid4()}.{ext}" if prefix else f"{uuid4()}.{ext}"


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_country_from_ip(ip):
    # TODO: Implement geoip lookup
    return 'Unknown'


def get_device_type(user_agent):
    ua = user_agent.lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return 'mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        return 'tablet'
    else:
        return 'desktop'
