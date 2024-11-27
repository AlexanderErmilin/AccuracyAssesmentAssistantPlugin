from .AccuracyAssessment import AccuracyAssessment

def classFactory(iface):
    """Функция для загрузки плагина в QGIS"""
    return AccuracyAssessment(iface)