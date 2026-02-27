import os
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


username_pattern = re.compile(r"^[\w.]+$", re.UNICODE)


def username_validator(value: str):
    if not username_pattern.match(value):
        raise ValidationError(_('Username может содержать буквы, цифры, подчёркивания и точки'))
    if len(value) < 3 or len(value) > 30:
        raise ValidationError(_('Длина username должна быть от 3 до 30 символов'))


def validate_avatar_file(file_obj):
    if not file_obj:
        return
    max_size_mb = 5
    if file_obj.size > max_size_mb * 1024 * 1024:
        raise ValidationError(_(f"Аватар не должен превышать {max_size_mb} MB"))
    ext = os.path.splitext(file_obj.name)[1].lower()
    allowed = {'.jpg', '.jpeg', '.png', '.webp'}
    if ext not in allowed:
        raise ValidationError(_('Разрешены только изображения jpg, png, webp'))
