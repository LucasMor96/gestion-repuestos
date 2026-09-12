from django import template

from apps.usuarios.choices import RUBROS_CHOICES


register = template.Library()


@register.filter
def rubro_display(value):
    return dict(RUBROS_CHOICES).get(value, value)
