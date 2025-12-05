# Файл для запуска

import sys
from PyQt5.QtWidgets import QApplication
from renamer_gui import RenamerWindow

def main():
    """Точка входа в приложение"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Современный стиль
    
    window = RenamerWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()