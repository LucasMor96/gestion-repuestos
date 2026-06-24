from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ConventionalPasswordValidator:
    """Require the usual mix expected from non-simple passwords."""

    def validate(self, password, user=None):
        missing_requirements = []
        if not any(char.islower() for char in password):
            missing_requirements.append(_('una letra minuscula'))
        if not any(char.isupper() for char in password):
            missing_requirements.append(_('una letra mayuscula'))
        if not any(char.isdigit() for char in password):
            missing_requirements.append(_('un numero'))
        if not any(not char.isalnum() for char in password):
            missing_requirements.append(_('un simbolo'))

        if missing_requirements:
            raise ValidationError(
                _('La contrasena debe incluir %(requirements)s.'),
                code='password_not_conventional',
                params={'requirements': ', '.join(missing_requirements)},
            )

    def get_help_text(self):
        return _(
            'Tu contrasena debe incluir mayusculas, minusculas, numeros y simbolos.'
        )
