from django import template

register = template.Library()


@register.simple_tag
def check_permission(admin_profile, permission_string):
    """
    Check if admin has permission.
    Usage: {% check_permission admin_profile "dashboard.view" as has_perm %}
           {% if has_perm %}...{% endif %}
    """
    if not admin_profile:
        return False
    
    if '.' in str(permission_string):
        module, action = str(permission_string).split('.', 1)
        return admin_profile.has_permission(module, action)
    
    return False


