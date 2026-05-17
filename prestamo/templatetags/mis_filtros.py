from django import template

register = template.Library()

@register.filter
def puntos(valor):
    """Convierte 20000 en 20.000"""
    try:
        return f"{int(valor):,}".replace(",", ".")
    except:
        return valor