"""
Context processor to add dashboard-specific data to all dashboard templates.
"""


def dashboard_context(request):
    """Add dashboard context data"""
    admin_profile = None
    
    # Safe access to admin_profile
    if request.user.is_authenticated:
        try:
            admin_profile = request.user.admin_profile
        except Exception:
            admin_profile = None
    
    def has_permission(permission_string):
        """Check permission in templates"""
        if not admin_profile or not permission_string:
            return False
        try:
            if '.' in str(permission_string):
                module, action = str(permission_string).split('.', 1)
                return admin_profile.has_permission(module, action)
        except Exception:
            return False
        return False
    
    return {
        'admin_profile': admin_profile,
        'has_permission': has_permission,
    }
