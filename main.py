# Файл для запуска

import sys
import traceback
import atexit
from PyQt5.QtWidgets import QApplication
from renamer_gui import RenamerWindow

def cleanup():
    """Функция очистки при выходе"""
    print("Выполняется cleanup...")
    # Даем время потокам завершиться
    import time
    time.sleep(0.5)

def handle_exception(exc_type, exc_value, exc_traceback):
    """Обработчик необработанных исключений"""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"Критическая ошибка:\n{error_msg}")
    
    # Пытаемся сохранить ошибку в файл
    try:
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(error_msg)
    except:
        pass
    
    cleanup()
    sys.exit(1)

def main():
    # Устанавливаем обработчик необработанных исключений
    sys.excepthook = handle_exception
    
    # Регистрируем функцию очистки
    atexit.register(cleanup)
    
    # Точка входа в приложение
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Устанавливаем обработку прерываний
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    try:
        window = RenamerWindow()
        window.show()
        
        result = app.exec_()
        
        # Очистка перед выходом
        cleanup()
        return result
        
    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
        cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())
