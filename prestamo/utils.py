from datetime import date, timedelta

# Feriados fijos en Paraguay (mes, día)
FERIADOS_FIJOS = [
    (1, 1),    # Año Nuevo
    (3, 1),    # Día de los Héroes
    (5, 1),    # Día del Trabajador
    (5, 15),   # Día de la Independencia
    (6, 12),   # Día de la Paz del Chaco
    (8, 15),   # Fundación de Asunción
    (9, 29),   # Victoria de Boquerón
    (12, 8),   # Virgen de Caacupé
    (12, 25),  # Navidad
]

def es_dia_habil(fecha):
    """Verifica si una fecha es día hábil (lunes a viernes y no feriado)"""
    # Verificar fin de semana (5 = sábado, 6 = domingo)
    if fecha.weekday() >= 5:
        return False
    
    # Verificar feriados fijos
    for mes, dia in FERIADOS_FIJOS:
        if fecha.month == mes and fecha.day == dia:
            return False
    
    return True

def sumar_dias_habiles(fecha_inicio, dias):
    """Suma días hábiles a una fecha (excluye sábados, domingos y feriados)"""
    fecha_actual = fecha_inicio
    dias_agregados = 0
    
    while dias_agregados < dias:
        fecha_actual += timedelta(days=1)
        if es_dia_habil(fecha_actual):
            dias_agregados += 1
    
    return fecha_actual