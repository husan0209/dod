from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_ticket_number(value):
    """Validate ticket number format DOD-YYYYMMDD-NNNN."""
    if not value.startswith('DOD-'):
        raise ValidationError(_('Ticket number must start with DOD-'))
    parts = value.split('-')
    if len(parts) != 3 or len(parts[2]) != 4:
        raise ValidationError(_('Invalid ticket number format'))


def validate_file_size(file):
    """Validate file size (max 10MB)."""
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        raise ValidationError(_('File size exceeds 10MB limit'))


def validate_file_type(file):
    """Validate file type."""
    allowed_types = [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ]
    if hasattr(file, 'content_type') and file.content_type not in allowed_types:
        raise ValidationError(_('Unsupported file type'))
