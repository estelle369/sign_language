import logging
import os

from PyQt5.QtGui import QFontDatabase


def load_custom_font_family():
    font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MonaS10.ttf")
    font_id = QFontDatabase.addApplicationFont(font_path)
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id != -1 else []
    if families:
        return families[0]
    logging.warning("Failed to load custom font: %s", font_path)
    return None
