# Графический интерфейс 

import os
import re
from typing import List, Dict, Any
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QCheckBox, QRadioButton, QSpinBox,
    QComboBox, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QHeaderView, QFormLayout, QButtonGroup, QTextEdit, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor

# Импортируем модули
try:
    from file_manager import FileManager
    from rules_engine import RulesEngine
   # from exif_processor import EXIFProcessor
    from undo_manager import UndoManager
except ImportError as e:
    print(f"Ошибка импорта модулей: {e}")
    print("Убедитесь, что все файлы находятся в одной директории:")
    print("  file_manager.py, rules_engine.py, exif_processor.py, undo_manager.py")
    raise


class PreviewWorker(QThread):
    # Воркер для предпросмотра изменений в отдельном потоке
    preview_finished = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, files: List[str], rules: Dict[str, Any], folder_path: str, 
                 sort_by: str = 'name', ascending: bool = True):
        super().__init__()
        self.files = files
        self.rules = rules
        self.folder_path = folder_path
        self.sort_by = sort_by
        self.ascending = ascending
        
    def run(self):
        # Выполнение предпросмотра в фоновом потоке
        try:
            results = {}
            total_files = len(self.files)
            
            # Создаем список пар (старое имя, индекс) для правильной нумерации
            for i, file_name in enumerate(self.files):
                # Обновляем прогресс
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
                # Применяем правила - передаем индекс i для нумерации
                new_name = RulesEngine.generate_new_name(file_name, i, self.rules)
                
                # Применяем EXIF данные если нужно
                if self.rules.get('enable_exif', False):
                    file_path = os.path.join(self.folder_path, file_name)
                #    new_name = EXIFProcessor.add_exif_to_filename(new_name, file_path, self.rules)
                
                results[file_name] = new_name
            
            self.preview_finished.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class RenamerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_manager = FileManager()
        self.undo_manager = UndoManager()
        self.current_files = []
        self.current_folder = ""
        self.preview_results = {}
        # Атрибуты сортировки
        self.current_sort_by = 'name'
        self.current_ascending = True
        self.original_files_order = []  # Сохраняем исходный порядок файлов
        self.setup_ui()

        QTimer.singleShot(0, self.initialize_disabled_fields)
    
    def initialize_disabled_fields(self):
        """Инициализация всех полей как отключенных при запуске"""
        self.toggle_replace_fields()
        self.toggle_replace_mode()
        self.toggle_prefix_suffix_fields()
        self.toggle_numbering_fields()
        self.toggle_exif_fields()
        
    def setup_ui(self):
        #Настройка пользовательского интерфейса
        self.setWindowTitle("Массовое переименование файлов")
        self.setGeometry(100, 100, 1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 1. Заголовок
        title_label = QLabel("Утилита массового переименования файлов")
        title_font = QFont("Arial", 18, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # 2. Секция выбора папки
        folder_group = self.create_folder_section()
        main_layout.addWidget(folder_group)
        
        # 3. Splitter для списка файлов и правил
        splitter = QSplitter(Qt.Horizontal)
        
        # Левая часть: список файлов
        file_list_widget = self.create_file_list_section()
        splitter.addWidget(file_list_widget)
        
        # Правая часть: правила переименования
        rules_widget = self.create_rules_section()
        splitter.addWidget(rules_widget)
        
        splitter.setSizes([500, 700])
        main_layout.addWidget(splitter, 1)
        
        # 4. Секция кнопок действий
        buttons_widget = self.create_action_buttons()
        main_layout.addWidget(buttons_widget)
        
        # 5. Статусная панель
        status_widget = self.create_status_bar()
        main_layout.addWidget(status_widget)
        
    def create_folder_section(self):
        # Секции выбора папки
        group = QGroupBox("📁 Выбор папки с файлами")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QHBoxLayout()
        
        # Поле пути
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("Выберите папку с файлами...")
        self.folder_path_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        layout.addWidget(self.folder_path_edit, 1)
        
        # Кнопка обзора
        browse_btn = QPushButton("Обзор...")
        browse_btn.setIcon(QIcon.fromTheme("folder-open"))
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        browse_btn.clicked.connect(self.browse_folder)
        layout.addWidget(browse_btn)
        
        # Кнопка загрузки
        load_btn = QPushButton("📥 Загрузить файлы")
        load_btn.setStyleSheet(""" 
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
                margin-left: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #219653;
            }
        """)
        load_btn.clicked.connect(self.load_files)
        layout.addWidget(load_btn)
        
        group.setLayout(layout)
        return group
        
    def create_file_list_section(self):
        # Секции со списком файлов
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Заголовок
        header = QLabel("Список файлов (предпросмотр)")
        header_font = QFont("Arial", 14, QFont.Bold)
        header.setFont(header_font)
        header.setStyleSheet("color: #34495e; padding: 7px;")
        layout.addWidget(header)
        
        # Таблица файлов
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["№", "Текущее имя", "Новое имя", "Статус"])
        
        # Настройка таблицы
        self.file_table.setStyleSheet("""
            QTableWidget {
                font-size: 11px;
                gridline-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #d6eaf8;
            }
        """)
        
        # Настройка размеров колонок
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        
        self.file_table.setColumnWidth(0, 40)
        self.file_table.setColumnWidth(3, 100)
        
        layout.addWidget(self.file_table)
        return widget
        
    def create_rules_section(self):
        # Секции с правилами переименования
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Заголовок
        header = QLabel("⚙️ Правила переименования")
        header_font = QFont("Arial", 14, QFont.Bold)
        header.setFont(header_font)
        header.setStyleSheet("color: #34495e; padding: 7px;")
        layout.addWidget(header)
        
        # Вкладки
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background: white;
            }
            QTabBar::tab {
                background: #ecf0f1;
                padding: 8px 12px;
                margin-right: 2px;
                border: 1px solid #bdc3c7;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #d6eaf8;
            }
        """)
        
        # Создание вкладок
        self.create_text_replace_tab()
        self.create_prefix_suffix_tab()
        self.create_numbering_tab()
        self.create_exif_tab()
        self.create_advanced_tab()
        
        layout.addWidget(self.tab_widget)
        return widget
        
    def create_text_replace_tab(self):
        """Вкладка 'Замена текста' (объединенная: обычная + regex)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Замена текста")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
        
        form = QFormLayout()
        # Уменьшаем расстояние между заголовками и полями ввода
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(5)
        
        # Чекбокс включения замены текста
        self.enable_replace = QCheckBox("Включить замену текста")
        self.enable_replace.setChecked(False)
        self.enable_replace.stateChanged.connect(self.toggle_replace_fields)
        form.addRow(self.enable_replace)
        
        # Переключатель режимов: обычная замена / регулярные выражения
        mode_group = QGroupBox("Режим замены")
        mode_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 0px;
                padding-top: 8px;
            }
        """)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(3)  # Уменьшаем расстояние между радио-кнопками
        
        self.simple_replace_mode = QRadioButton("Простая замена текста")
        self.simple_replace_mode.setChecked(True)
        self.regex_replace_mode = QRadioButton("Регулярные выражения")
        
        self.simple_replace_mode.toggled.connect(self.toggle_replace_mode)
        self.regex_replace_mode.toggled.connect(self.toggle_replace_mode)
        
        mode_layout.addWidget(self.simple_replace_mode)
        mode_layout.addWidget(self.regex_replace_mode)
        form.addRow(mode_group)
        
        # Поле "Заменить" - используется в обоих режимах
        self.replace_from = QLineEdit()
        self.replace_from.setPlaceholderText("Например: IMG_ (для простой замены) или (\\d{4})-(\\d{2})-(\\d{2}) (для regex)")
        form.addRow("Найти (шаблон):", self.replace_from)
        
        # Поле "На" - используется в обоих режимах
        self.replace_to = QLineEdit()
        self.replace_to.setPlaceholderText("Например: Photo_ (для простой замены) или \\3.\\2.\\1 (для regex)")
        form.addRow("Заменить на:", self.replace_to)
        
        # Поля для простого режима
        self.simple_options_group = QGroupBox("Параметры простой замены")
        self.simple_options_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 0px;
                padding-top: 8px;
            }
        """)
        simple_options_layout = QVBoxLayout(self.simple_options_group)
        simple_options_layout.setSpacing(3)  # Уменьшаем расстояние между чекбоксами
        
        self.case_sensitive = QCheckBox("Учитывать регистр")
        self.replace_all = QCheckBox("Заменить все вхождения")
        self.replace_all.setChecked(True)
        
        simple_options_layout.addWidget(self.case_sensitive)
        simple_options_layout.addWidget(self.replace_all)
        form.addRow(self.simple_options_group)
        
        # Поля для режима регулярных выражений
        self.regex_options_group = QGroupBox("Параметры регулярных выражений")
        self.regex_options_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 0px;
                padding-top: 8px;
            }
        """)
        regex_options_layout = QVBoxLayout(self.regex_options_group)
        regex_options_layout.setSpacing(3)
        
        self.regex_ignore_case = QCheckBox("Игнорировать регистр")
        self.regex_dotall = QCheckBox("Точка соответствует переводу строки")
        
        regex_options_layout.addWidget(self.regex_ignore_case)
        regex_options_layout.addWidget(self.regex_dotall)
        form.addRow(self.regex_options_group)
        
        # Примеры использования - В ДВЕ КОЛОНКИ
        examples_group = QGroupBox("Примеры использования")
        examples_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 0px;
                padding-top: 8px;
            }
        """)
        examples_layout = QVBoxLayout(examples_group)
        examples_layout.setSpacing(5)
        
        # Создаем контейнер для двух колонок
        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(15)  # Отступ между колонками
        
        # Левая колонка - Примеры простой замены
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        simple_examples = QLabel("<b>Примеры простой замены:</b>")
        simple_examples.setStyleSheet("color: #2c3e50;")
        left_layout.addWidget(simple_examples)
        
        simple_examples_list = [
            ("'IMG_1234.jpg'", "'Photo_1234.jpg'"),
            ("'DSC_'", "'Photo_'"),
            ("'vacation '", "'' (удаление)"),
            ("'2019_'", "'2024_'"),
            ("'photo.jpg'", "'image.jpg'"),
            ("'IMG'", "'Photo'")
        ]
        
        for from_example, to_example in simple_examples_list:
            example_widget = QWidget()
            example_layout = QHBoxLayout(example_widget)
            example_layout.setContentsMargins(0, 0, 0, 0)
            example_layout.setSpacing(3)
            
            from_label = QLabel(from_example)
            from_label.setStyleSheet("color: #7f8c8d; font-size: 10px; font-family: monospace;")
            
            arrow_label = QLabel("→")
            arrow_label.setStyleSheet("color: #95a5a6; font-size: 10px; padding: 0 5px;")
            
            to_label = QLabel(to_example)
            to_label.setStyleSheet("color: #7f8c8d; font-size: 10px; font-family: monospace;")
            
            example_layout.addWidget(from_label)
            example_layout.addWidget(arrow_label)
            example_layout.addWidget(to_label)
            example_layout.addStretch()
            
            left_layout.addWidget(example_widget)
        
        left_layout.addStretch()
        columns_layout.addWidget(left_column, 1)
        
        # Правая колонка - Примеры регулярных выражений
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        regex_examples = QLabel("<b>Примеры регулярных выражений:</b>")
        regex_examples.setStyleSheet("color: #2c3e50;")
        right_layout.addWidget(regex_examples)
        
        regex_examples_list = [
            ("Дата: '(\\d{4})-(\\d{2})-(\\d{2})'", "'\\3.\\2.\\1'"),
            ("Пробелы: '\\s+'", "''"),
            ("Числа: '.*?(\\d+).*'", "'\\1'"),
            ("Перестановка: '(.+)_(\\d+)\\.(.+)'", "'\\2_\\1.\\3'"),
            ("Удаление цифр: '\\d+'", "''"),
            ("Формат: 'IMG_(\\d{4})\\.(.+)'", "'Photo_\\1.\\2'")
        ]
        
        for from_example, to_example in regex_examples_list:
            example_widget = QWidget()
            example_layout = QHBoxLayout(example_widget)
            example_layout.setContentsMargins(0, 0, 0, 0)
            example_layout.setSpacing(3)
            
            from_label = QLabel(from_example)
            from_label.setStyleSheet("color: #7f8c8d; font-size: 10px; font-family: monospace;")
            
            arrow_label = QLabel("→")
            arrow_label.setStyleSheet("color: #95a5a6; font-size: 10px; padding: 0 5px;")
            
            to_label = QLabel(to_example)
            to_label.setStyleSheet("color: #7f8c8d; font-size: 10px; font-family: monospace;")
            
            example_layout.addWidget(from_label)
            example_layout.addWidget(arrow_label)
            example_layout.addWidget(to_label)
            example_layout.addStretch()
            
            right_layout.addWidget(example_widget)
        
        right_layout.addStretch()
        columns_layout.addWidget(right_column, 1)
        
        # Добавляем пояснение
        explanation = QLabel("<i>Примечание: в регулярных выражениях используйте \\\\1, \\\\2 и т.д. для ссылок на группы</i>")
        explanation.setStyleSheet("color: #7f8c8d; font-size: 9px; margin-top: 10px;")
        explanation.setAlignment(Qt.AlignCenter)
        
        examples_layout.addWidget(columns_container)
        examples_layout.addWidget(explanation)
        form.addRow(examples_group)
        
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Замена текста")
    
    def toggle_replace_mode(self):
        """Переключение между простой заменой и регулярными выражениями"""
        is_simple_mode = self.simple_replace_mode.isChecked()
        
        # Показываем/скрываем соответствующие группы параметров
        self.simple_options_group.setVisible(is_simple_mode)
        self.regex_options_group.setVisible(not is_simple_mode)
        
        # Обновляем подсказки в полях ввода
        if is_simple_mode:
            self.replace_from.setPlaceholderText("Например: IMG_ или vacation")
            self.replace_to.setPlaceholderText("Например: Photo_ или holiday")
        else:
            self.replace_from.setPlaceholderText("Например: (\\d{4})-(\\d{2})-(\\d{2}) или \\s+")
            self.replace_to.setPlaceholderText("Например: \\3.\\2.\\1 или _")
        
        # Обновляем доступность полей
        if self.enable_replace.isChecked():
            self.case_sensitive.setEnabled(is_simple_mode)
            self.replace_all.setEnabled(is_simple_mode)
            self.regex_ignore_case.setEnabled(not is_simple_mode)
            self.regex_dotall.setEnabled(not is_simple_mode)
    
    def toggle_replace_fields(self):
        """Включение/выключение полей замены текста"""
        enabled = self.enable_replace.isChecked()
        self.simple_replace_mode.setEnabled(enabled)
        self.regex_replace_mode.setEnabled(enabled)
        self.replace_from.setEnabled(enabled)
        self.replace_to.setEnabled(enabled)
        
        is_simple_mode = self.simple_replace_mode.isChecked()
        self.case_sensitive.setEnabled(enabled and is_simple_mode)
        self.replace_all.setEnabled(enabled and is_simple_mode)
        self.regex_ignore_case.setEnabled(enabled and not is_simple_mode)
        self.regex_dotall.setEnabled(enabled and not is_simple_mode)
        
        # Меняем стиль для отключенных полей
        style = "color: #7f8c8d;" if not enabled else ""
        self.replace_from.setStyleSheet(style)
        self.replace_to.setStyleSheet(style)
        self.case_sensitive.setStyleSheet(style)
        self.replace_all.setStyleSheet(style)
        self.regex_ignore_case.setStyleSheet(style)
        self.regex_dotall.setStyleSheet(style)
        
    def create_prefix_suffix_tab(self):
        # Вкладка 'Префикс/Суффикс'
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Добавление префикса и/или суффикса")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
        
        form = QFormLayout()
        # Уменьшаем расстояние между заголовками и полями ввода
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(5)
        
        # Чекбокс включения префикса/суффикса
        self.enable_prefix_suffix = QCheckBox("Включить префикс/суффикс")
        self.enable_prefix_suffix.setChecked(False)
        self.enable_prefix_suffix.stateChanged.connect(self.toggle_prefix_suffix_fields)
        form.addRow(self.enable_prefix_suffix)
        
        # Префикс
        self.prefix_text = QLineEdit()
        self.prefix_text.setPlaceholderText("Например: vacation_")
        form.addRow("Префикс:", self.prefix_text)
        
        # Суффикс
        self.suffix_text = QLineEdit()
        self.suffix_text.setPlaceholderText("Например: _edited")
        form.addRow("Суффикс:", self.suffix_text)
        
        # Радиокнопки для позиции суффикса
        suffix_group = QGroupBox("Позиция суффикса")
        suffix_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 0px;
                padding-top: 8px;
            }
        """)
        suffix_layout = QVBoxLayout(suffix_group)
        suffix_layout.setSpacing(3)
        
        self.suffix_before_ext = QRadioButton("Перед расширением (file_suffix.ext)")
        self.suffix_before_ext.setChecked(True)
        self.suffix_after_ext = QRadioButton("После расширения (file.ext_suffix)")
        
        suffix_layout.addWidget(self.suffix_before_ext)
        suffix_layout.addWidget(self.suffix_after_ext)
        form.addRow(suffix_group)
        
        # Пример
        example_label = QLabel("Пример: 'photo.jpg' → 'vacation_photo_edited.jpg'")
        example_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        form.addRow(example_label)
        
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Префикс/Суффикс")
        
    def toggle_prefix_suffix_fields(self):
        """Включение/выключение полей префикса/суффикса"""
        enabled = self.enable_prefix_suffix.isChecked()
        self.prefix_text.setEnabled(enabled)
        self.suffix_text.setEnabled(enabled)
        self.suffix_before_ext.setEnabled(enabled)
        self.suffix_after_ext.setEnabled(enabled)
        
        # Меняем стиль для отключенных полей
        style = "color: #7f8c8d;" if not enabled else ""
        self.prefix_text.setStyleSheet(style)
        self.suffix_text.setStyleSheet(style)
        
    def create_numbering_tab(self):
        """Вкладка 'Нумерация'"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Параметры нумерации")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
        
        form = QFormLayout()
        # Уменьшаем расстояние между заголовками и полями ввода
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(5)
        
        # Чекбокс включения нумерации
        self.enable_numbering = QCheckBox("Включить нумерацию")
        self.enable_numbering.setChecked(False)
        self.enable_numbering.stateChanged.connect(self.toggle_numbering_fields)
        form.addRow(self.enable_numbering)
        
        # Начальный номер
        start_layout = QHBoxLayout()
        self.start_number = QSpinBox()
        self.start_number.setRange(1, 9999)
        self.start_number.setValue(1)
        start_layout.addWidget(self.start_number)
        start_layout.addStretch()
        form.addRow("Начальный номер:", start_layout)
        
        # Количество цифр
        digits_layout = QHBoxLayout()
        self.digits_count = QSpinBox()
        self.digits_count.setRange(1, 6)
        self.digits_count.setValue(3)
        digits_layout.addWidget(self.digits_count)
        digits_layout.addStretch()
        form.addRow("Количество цифр:", digits_layout)
        
        # Разделитель
        self.number_separator = QLineEdit()
        self.number_separator.setText("_")
        self.number_separator.setMaxLength(3)
        form.addRow("Разделитель:", self.number_separator)
        
        # Позиция номера
        position_group = QButtonGroup()
        pos_layout = QHBoxLayout()
        
        self.number_prefix = QRadioButton("Префикс (001_file)")
        self.number_suffix = QRadioButton("Суффикс (file_001)")
        self.number_suffix.setChecked(True)
        
        position_group.addButton(self.number_prefix)
        position_group.addButton(self.number_suffix)
        
        pos_layout.addWidget(self.number_prefix)
        pos_layout.addWidget(self.number_suffix)
        form.addRow("Позиция номера:", pos_layout)
        
        # Пример
        example_label = QLabel("Пример: 'photo.jpg' → 'photo_001.jpg'")
        example_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        form.addRow(example_label)
        
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Нумерация")
        
    def toggle_numbering_fields(self):
        """Включение/выключение полей нумерации"""
        enabled = self.enable_numbering.isChecked()
        self.start_number.setEnabled(enabled)
        self.digits_count.setEnabled(enabled)
        self.number_separator.setEnabled(enabled)
        self.number_prefix.setEnabled(enabled)
        self.number_suffix.setEnabled(enabled)
        
        # Меняем стиль для отключенных полей
        style = "color: #7f8c8d;" if not enabled else ""
        self.number_separator.setStyleSheet(style)
        
    def create_exif_tab(self):
        # Вкладка 'EXIF данные'
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Использование метаданных EXIF")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
        
        form = QFormLayout()
        # Уменьшаем расстояние между заголовками и полями ввода
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(5)
        
        # Включить EXIF
        self.enable_exif = QCheckBox("Включить EXIF данные")
        self.enable_exif.setChecked(False)
        self.enable_exif.stateChanged.connect(self.toggle_exif_fields)
        form.addRow(self.enable_exif)
        
        # Формат даты
        format_layout = QHBoxLayout()
        self.date_format = QComboBox()
        self.date_format.addItems([
            "YYYY-MM-DD",
            "DD-MM-YYYY", 
            "YYYYMMDD",
            "MM-DD-YYYY",
            "YY-MM-DD",
            "DD.MM.YYYY"
        ])
        format_layout.addWidget(self.date_format)
        format_layout.addStretch()
        form.addRow("Формат даты:", format_layout)
        
        # Позиция даты
        date_pos_layout = QHBoxLayout()
        self.date_prefix = QRadioButton("Префикс")
        self.date_prefix.setChecked(True)
        self.date_suffix = QRadioButton("Суффикс")
        
        date_pos_layout.addWidget(self.date_prefix)
        date_pos_layout.addWidget(self.date_suffix)
        date_pos_layout.addStretch()
        form.addRow("Позиция даты:", date_pos_layout)
        
        # Разделитель
        self.exif_separator = QLineEdit()
        self.exif_separator.setText("_")
        form.addRow("Разделитель:", self.exif_separator)
        
        # Дополнительные EXIF данные
        exif_extras = QGroupBox("Дополнительные данные EXIF")
        exif_extras.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 0px;
                padding-top: 8px;
            }
        """)
        extras_layout = QVBoxLayout(exif_extras)
        extras_layout.setSpacing(3)
        
        self.use_camera_model = QCheckBox("Модель камеры")
        self.use_exposure = QCheckBox("Параметры экспозиции")
        self.use_gps = QCheckBox("Координаты GPS")
        
        extras_layout.addWidget(self.use_camera_model)
        extras_layout.addWidget(self.use_exposure)
        extras_layout.addWidget(self.use_gps)
        
        form.addRow(exif_extras)
        
        # Пример
        example_label = QLabel("Пример: 'IMG_1234.jpg' → '2023-12-01_1234.jpg'")
        example_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        form.addRow(example_label)
        
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "EXIF")
        
    def toggle_exif_fields(self):
        """Включение/выключение полей EXIF"""
        enabled = self.enable_exif.isChecked()
        self.date_format.setEnabled(enabled)
        self.date_prefix.setEnabled(enabled)
        self.date_suffix.setEnabled(enabled)
        self.exif_separator.setEnabled(enabled)
        self.use_camera_model.setEnabled(enabled)
        self.use_exposure.setEnabled(enabled)
        self.use_gps.setEnabled(enabled)
        
        # Меняем стиль для отключенных полей
        style = "color: #7f8c8d;" if not enabled else ""
        self.exif_separator.setStyleSheet(style)
        
    def create_advanced_tab(self):
        # Вкладка 'Дополнительно'
        tab = QWidget()
        layout = QVBoxLayout(tab)
    
        # Группа 1: Расширения
        ext_group = QGroupBox("Обработка расширений файлов")
        ext_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
    
        ext_layout = QVBoxLayout(ext_group)
        ext_layout.setSpacing(3)
    
        self.lowercase_ext = QCheckBox("Приводить расширения к нижнему регистру (.JPG → .jpg)")
        self.lowercase_ext.setChecked(True)
        self.remove_spaces = QCheckBox("Удалять пробелы в именах файлов")
        self.keep_original = QCheckBox("Сохранять копию оригинальных файлов")
    
        ext_layout.addWidget(self.lowercase_ext)
        ext_layout.addWidget(self.remove_spaces)
        ext_layout.addWidget(self.keep_original)
    
        # Группа 2: Фильтрация
        filter_group = QGroupBox("Фильтрация файлов")
        filter_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
    
        filter_layout = QFormLayout(filter_group)
        filter_layout.setHorizontalSpacing(8)
        filter_layout.setVerticalSpacing(5)

        self.filter_extensions = QLineEdit()
        self.filter_extensions.setPlaceholderText("jpg, png, pdf, docx (через запятую)")
        filter_layout.addRow("Расширения:", self.filter_extensions)
    
        self.min_size = QSpinBox()
        self.min_size.setSuffix(" KB")
        self.min_size.setRange(0, 100000)
        filter_layout.addRow("Минимальный размер:", self.min_size)
    
        # Группа 3: Сортировка
        sort_group = QGroupBox("Сортировка файлов перед переименованием")
        sort_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
        """)
    
        # Создаем группу для радиокнопок критерия сортировки
        sort_criteria_group = QGroupBox("Критерий сортировки")
        sort_criteria_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
            }
        """)
        sort_criteria_layout = QVBoxLayout(sort_criteria_group)
        sort_criteria_layout.setSpacing(3)
        
        self.sort_by_name = QRadioButton("По имени")
        self.sort_by_name.setChecked(True)
        self.sort_by_date = QRadioButton("По дате создания")
        self.sort_by_size = QRadioButton("По размеру")
        
        # Создаем ButtonGroup для связывания радиокнопок критерия
        self.criteria_button_group = QButtonGroup()
        self.criteria_button_group.addButton(self.sort_by_name, 1)
        self.criteria_button_group.addButton(self.sort_by_date, 2)
        self.criteria_button_group.addButton(self.sort_by_size, 3)
        
        sort_criteria_layout.addWidget(self.sort_by_name)
        sort_criteria_layout.addWidget(self.sort_by_date)
        sort_criteria_layout.addWidget(self.sort_by_size)
    
        # Создаем группу для радиокнопок направления сортировки
        sort_order_group = QGroupBox("Порядок сортировки")
        sort_order_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
            }
        """)
        sort_order_layout = QVBoxLayout(sort_order_group)
        sort_order_layout.setSpacing(3)
        
        self.sort_asc = QRadioButton("По возрастанию")
        self.sort_asc.setChecked(True)
        self.sort_desc = QRadioButton("По убыванию")
        
        # Создаем ButtonGroup для связывания радиокнопок направления
        self.order_button_group = QButtonGroup()
        self.order_button_group.addButton(self.sort_asc, 1)
        self.order_button_group.addButton(self.sort_desc, 2)
        
        sort_order_layout.addWidget(self.sort_asc)
        sort_order_layout.addWidget(self.sort_desc)
    
        # Добавляем обе группы в основную группу сортировки
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(sort_criteria_group, 1)
        sort_layout.addWidget(sort_order_group, 1)
        sort_group.setLayout(sort_layout)
    
        layout.addWidget(ext_group)
        layout.addWidget(filter_group)
        layout.addWidget(sort_group)
        layout.addStretch()
    
        self.tab_widget.addTab(tab, "Дополнительно")
        
    def create_action_buttons(self):
        # Создание секции с кнопками действий
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
        # Добавляем растяжение для центрирования кнопок
        layout.addStretch(1)
        
        # Стили для кнопок
        button_style = """
            QPushButton {
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 4px;
                border: none;
            }
        """
        
        # Кнопка предпросмотра
        self.preview_btn = QPushButton("👁️ Предпросмотр")
        self.preview_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        self.preview_btn.clicked.connect(self.preview_changes)
        self.preview_btn.setEnabled(False)
        layout.addWidget(self.preview_btn)
        
        # Кнопка сортировки
        self.sort_btn = QPushButton("🔄 Сортировать")
        self.sort_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #9b59b6;
                color: white;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        self.sort_btn.clicked.connect(self.resort_files)
        self.sort_btn.setEnabled(False)
        layout.addWidget(self.sort_btn)
        
        # Кнопка применения
        self.apply_btn = QPushButton("✅ Применить переименование")
        self.apply_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #2ecc71;
                color: white;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        self.apply_btn.clicked.connect(self.apply_changes)
        self.apply_btn.setEnabled(False)
        layout.addWidget(self.apply_btn)
        
        # Кнопка отката
        self.undo_btn = QPushButton("↩️ Откатить последнюю операцию")
        self.undo_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        self.undo_btn.clicked.connect(self.undo_changes)
        self.undo_btn.setEnabled(False)
        layout.addWidget(self.undo_btn)
        
        # Кнопка очистки
        self.clear_btn = QPushButton("🗑️ Очистить правила")
        self.clear_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #f39c12;
                color: white;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_rules)
        layout.addWidget(self.clear_btn)
        
        layout.addStretch(1)
        
        return widget
        
    def create_status_bar(self):
        """Создание статусной панели"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Статус
        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                font-size: 11px;
            }
        """)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 2px;
            }
        """)
        
        # Счетчик файлов
        self.file_counter = QLabel("Файлов: 0")
        self.file_counter.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #34495e;
                color: white;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
                min-width: 80px;
                text-align: center;
            }
        """)
        
        layout.addWidget(self.status_label, 1)
        layout.addWidget(self.progress_bar, 2)
        layout.addWidget(self.file_counter)
        
        return widget
        
    def browse_folder(self):
        # Выбор папки
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Выберите папку",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder:
            self.folder_path_edit.setText(folder)
            self.current_folder = folder
            self.status_label.setText(f"Выбрана папка: {os.path.basename(folder)}")
            
    def load_files(self):
        # Загрузка файлов из папки с фильтрацией и сортировкой
        folder_path = self.folder_path_edit.text()
        
        if not folder_path:
            QMessageBox.warning(self, "Внимание", "Сначала выберите папку!")
            return
            
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "Ошибка", "Указанная папка не существует!")
            return
            
        try:
            # Получаем список всех файлов из папки
            all_files = self.file_manager.get_files_from_folder(folder_path)
            
            if not all_files:
                QMessageBox.information(self, "Информация", "В выбранной папке нет файлов")
                return
            
            # Сохраняем исходный порядок файлов (без сортировки)
            self.original_files_order = all_files.copy()
            
            # Применяем фильтрацию по расширениям
            extensions = self.filter_extensions.text()
            filtered_files = self.file_manager.filter_files_by_extension(all_files, extensions)
            
            # Применяем фильтрацию по размеру
            min_size = self.min_size.value()
            filtered_files = self.file_manager.filter_files_by_size(filtered_files, folder_path, min_size)
            
            if not filtered_files:
                QMessageBox.warning(self, "Внимание", 
                                  "Нет файлов, соответствующих фильтрам. Измените параметры фильтрации.")
                return
            
            # Применяем сортировку
            sort_by = 'name'
            if self.sort_by_date.isChecked():
                sort_by = 'date'
            elif self.sort_by_size.isChecked():
                sort_by = 'size'
            
            ascending = self.sort_asc.isChecked()
            
            # Обновляем сохраненные параметры
            self.current_sort_by = sort_by
            self.current_ascending = ascending
            
            # СОРТИРУЕМ файлы (только отфильтрованные)
            sorted_files = self.file_manager.sort_files(filtered_files, folder_path, sort_by, ascending)
            
            # Сохраняем текущий список файлов
            self.current_files = sorted_files
            self.current_folder = folder_path
            
            # Заполняем таблицу
            self.file_table.setRowCount(len(sorted_files))
            
            for i, filename in enumerate(sorted_files):
                # Номер
                num_item = QTableWidgetItem(str(i + 1))
                num_item.setTextAlignment(Qt.AlignCenter)
                num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
                self.file_table.setItem(i, 0, num_item)
                
                # Текущее имя
                old_item = QTableWidgetItem(filename)
                old_item.setFlags(old_item.flags() & ~Qt.ItemIsEditable)
                self.file_table.setItem(i, 1, old_item)
                
                # Новое имя (пока такое же)
                new_item = QTableWidgetItem(filename)
                new_item.setFlags(new_item.flags() & ~Qt.ItemIsEditable)
                self.file_table.setItem(i, 2, new_item)
                
                # Статус
                status_item = QTableWidgetItem("⏳ Ожидание")
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                status_item.setBackground(QColor("#fff9e6"))
                status_item.setForeground(QColor("#f39c12"))
                self.file_table.setItem(i, 3, status_item)
            
            # Обновляем счетчик и статус
            file_count = len(sorted_files)
            self.file_counter.setText(f"Файлов: {file_count}")
            
            # Показываем информацию о фильтрации
            filter_info = []
            if extensions:
                filter_info.append(f"расширения: {extensions}")
            if min_size > 0:
                filter_info.append(f"мин. размер: {min_size}KB")
            
            status_text = f"Загружено {file_count} файлов"
            if filter_info:
                status_text += f" (фильтр: {', '.join(filter_info)})"
            status_text += f", отсортировано по {sort_by} ({'возрастанию' if ascending else 'убыванию'})"
            
            # Включаем кнопки
            self.preview_btn.setEnabled(True)
            self.sort_btn.setEnabled(True)
            self.apply_btn.setEnabled(False)
            
            # Обновляем состояние кнопки отката
            self.undo_btn.setEnabled(self.undo_manager.has_operations())
            
            self.status_label.setText(status_text)
            self.progress_bar.setValue(0)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файлы:\n{str(e)}")
            self.status_label.setText("Ошибка при загрузке файлов")
            
    def resort_files(self):
        """Пересортировать файлы с текущими параметрами"""
        if not self.current_folder:
            QMessageBox.warning(self, "Внимание", "Сначала загрузите файлы!")
            return
        
        try:
            # Получаем все файлы из папки
            all_files = self.file_manager.get_files_from_folder(self.current_folder)
            
            # Применяем фильтрацию по расширениям
            extensions = self.filter_extensions.text()
            filtered_files = self.file_manager.filter_files_by_extension(all_files, extensions)
            
            # Применяем фильтрация по размеру
            min_size = self.min_size.value()
            filtered_files = self.file_manager.filter_files_by_size(filtered_files, self.current_folder, min_size)
            
            if not filtered_files:
                QMessageBox.warning(self, "Внимание", 
                                  "Нет файлов, соответствующих фильтрам. Измените параметры фильтрации.")
                return
            
            # Получаем актуальные настройки сортировки из интерфейса
            sort_by = 'name'
            if self.sort_by_date.isChecked():
                sort_by = 'date'
            elif self.sort_by_size.isChecked():
                sort_by = 'size'
            
            ascending = self.sort_asc.isChecked()
            
            # Обновляем сохраненные параметры
            self.current_sort_by = sort_by
            self.current_ascending = ascending
            
            # Сортируем отфильтрованные файлы
            sorted_files = self.file_manager.sort_files(filtered_files, self.current_folder, sort_by, ascending)
            
            # Обновляем текущий список файлов
            self.current_files = sorted_files
            
            # Обновляем таблицу
            self.file_table.setRowCount(len(sorted_files))
            
            for i, filename in enumerate(sorted_files):
                # Номер
                num_item = QTableWidgetItem(str(i + 1))
                num_item.setTextAlignment(Qt.AlignCenter)
                num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
                self.file_table.setItem(i, 0, num_item)
                
                # Текущее имя
                old_item = QTableWidgetItem(filename)
                old_item.setFlags(old_item.flags() & ~Qt.ItemIsEditable)
                self.file_table.setItem(i, 1, old_item)
                
                # Сбрасываем новое имя
                new_item = QTableWidgetItem(filename)
                new_item.setFlags(new_item.flags() & ~Qt.ItemIsEditable)
                self.file_table.setItem(i, 2, new_item)
                
                # Сбрасываем статус
                status_item = QTableWidgetItem("⏳ Ожидание")
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                status_item.setBackground(QColor("#fff9e6"))
                status_item.setForeground(QColor("#f39c12"))
                self.file_table.setItem(i, 3, status_item)
            
            # Обновляем счетчик
            file_count = len(sorted_files)
            self.file_counter.setText(f"Файлов: {file_count}")
            
            # Показываем информацию о фильтрации
            filter_info = []
            if extensions:
                filter_info.append(f"расширения: {extensions}")
            if min_size > 0:
                filter_info.append(f"мин. размер: {min_size}KB")
            
            status_text = f"Отсортировано {file_count} файлов"
            if filter_info:
                status_text += f" (фильтр: {', '.join(filter_info)})"
            status_text += f" по {sort_by} ({'возрастанию' if ascending else 'убыванию'})"
            
            self.status_label.setText(status_text)
            self.preview_results.clear()  # Сбрасываем предпросмотр
            self.apply_btn.setEnabled(False)  # Отключаем кнопку применения
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сортировке:\n{str(e)}")
            
    def collect_rules(self) -> Dict[str, Any]:
        # Сбор всех правил из интерфейса
        is_simple_mode = self.simple_replace_mode.isChecked()
        
        rules = {
            # Замена текста (объединенная)
            'enable_replace': self.enable_replace.isChecked(),
            'replace_from': self.replace_from.text(),
            'replace_to': self.replace_to.text(),
            
            # Параметры для простого режима
            'simple_mode': is_simple_mode,
            'case_sensitive': self.case_sensitive.isChecked() if is_simple_mode else False,
            'replace_all': self.replace_all.isChecked() if is_simple_mode else True,
            
            # Параметры для режима регулярных выражений
            'enable_regex': not is_simple_mode and self.enable_replace.isChecked(),
            'regex_pattern': self.replace_from.text() if not is_simple_mode else '',
            'regex_replacement': self.replace_to.text() if not is_simple_mode else '',
            'regex_ignore_case': self.regex_ignore_case.isChecked() if not is_simple_mode else False,
            'regex_dotall': self.regex_dotall.isChecked() if not is_simple_mode else False,
            
            # Префикс/суффикс
            'enable_prefix_suffix': self.enable_prefix_suffix.isChecked(),
            'prefix': self.prefix_text.text(),
            'suffix': self.suffix_text.text(),
            'suffix_before_ext': self.suffix_before_ext.isChecked(),
            
            # Нумерация
            'enable_numbering': self.enable_numbering.isChecked(),
            'start_number': self.start_number.value(),
            'digits_count': self.digits_count.value(),
            'number_separator': self.number_separator.text(),
            'number_position': 'prefix' if self.number_prefix.isChecked() else 'suffix',
            
            # EXIF
            'enable_exif': self.enable_exif.isChecked(),
            'date_format': self.date_format.currentText(),
            'exif_position': 'prefix' if self.date_prefix.isChecked() else 'suffix',
            'exif_separator': self.exif_separator.text(),
            'use_camera_model': self.use_camera_model.isChecked(),
            'use_exposure': self.use_exposure.isChecked(),
            'use_gps': self.use_gps.isChecked(),
            
            # Дополнительно
            'lowercase_ext': self.lowercase_ext.isChecked(),
            'remove_spaces': self.remove_spaces.isChecked(),
            'keep_original': self.keep_original.isChecked(),
            
            # Параметры сортировки
            'sort_by': self.current_sort_by,
            'ascending': self.current_ascending,
        }
        
        return rules
        
    def preview_changes(self):
        # Предпросмотр изменений на основе правил
        if not self.current_files or not self.current_folder:
            QMessageBox.warning(self, "Внимание", "Сначала загрузите файлы!")
            return
        
        # Блокируем кнопки во время обработки
        self.preview_btn.setEnabled(False)
        self.sort_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.status_label.setText("Выполняется предпросмотр...")
        self.progress_bar.setValue(0)
        
        # Собираем правила
        rules = self.collect_rules()
        
        # Получаем параметры сортировки
        sort_by = self.current_sort_by
        ascending = self.current_ascending
        
        # Запускаем воркер в отдельном потоке
        self.worker = PreviewWorker(self.current_files, rules, self.current_folder, sort_by, ascending)
        self.worker.preview_finished.connect(self.on_preview_finished)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.error_occurred.connect(self.on_preview_error)
        self.worker.start()
        
    def on_preview_finished(self, results: Dict[str, str]):
        # Обработка завершения предпросмотра
        self.preview_results = results
        
        # Обновляем таблицу
        for i in range(self.file_table.rowCount()):
            current_name = self.file_table.item(i, 1).text()
            new_name = results.get(current_name, current_name)
            
            # Обновляем новое имя
            new_item = QTableWidgetItem(new_name)
            new_item.setFlags(new_item.flags() & ~Qt.ItemIsEditable)
            self.file_table.setItem(i, 2, new_item)
            
            # Обновляем статус
            if new_name != current_name:
                status_item = self.file_table.item(i, 3)
                status_item.setText("✅ Изменено")
                status_item.setBackground(QColor("#d5f4e6"))
                status_item.setForeground(QColor("#27ae60"))
            else:
                status_item = self.file_table.item(i, 3)
                status_item.setText("⏳ Ожидание")
                status_item.setBackground(QColor("#fff9e6"))
                status_item.setForeground(QColor("#f39c12"))
        
        # Разблокируем кнопки
        self.preview_btn.setEnabled(True)
        self.sort_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)
        self.status_label.setText("Предпросмотр выполнен")
        self.progress_bar.setValue(100)
        
    def on_preview_error(self, error_msg: str):
        # Обработка ошибки предпросмотра
        self.preview_btn.setEnabled(True)
        self.sort_btn.setEnabled(True)
        self.apply_btn.setEnabled(False)
        self.status_label.setText("Ошибка при предпросмотре")
        QMessageBox.critical(self, "Ошибка", f"Ошибка при предпросмотре:\n{error_msg}")
            
    def apply_changes(self):
        # Применение изменений (переименование файлов)
        if not self.preview_results:
            QMessageBox.warning(self, "Внимание", "Сначала выполните предпросмотр!")
            return
        
        folder_path = self.current_folder
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "Ошибка", "Папка не существует!")
            return
        
        # Подсчитываем сколько файлов будет изменено
        changes = []
        changed_files = []
        
        # Используем preview_results для получения новых имен
        for i in range(self.file_table.rowCount()):
            current_name = self.file_table.item(i, 1).text()
            new_name = self.preview_results.get(current_name, current_name)
            
            if current_name != new_name:
                changes.append({'old': current_name, 'new': new_name})
                changed_files.append(current_name)
        
        if not changes:
            QMessageBox.information(self, "Информация", "Нет изменений для применения")
            return
        
        # Подтверждение
        reply = QMessageBox.question(
            self, 
            "Подтверждение",
            f"Вы уверены, что хотите переименовать {len(changes)} файлов?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Создаем резервную копию если нужно
        keep_original = self.keep_original.isChecked()
        if keep_original:
            backup_path = self.undo_manager.create_backup(folder_path, changed_files)
            if backup_path:
                self.status_label.setText(f"Создана резервная копия в {backup_path}")
        
        # ВАЖНО: Сохраняем копию изменений ДО переименования
        changes_copy = changes.copy()
        
        # Выполняем переименование
        success_count = 0
        error_count = 0
        failed_files = []
        
        for change in changes:
            old_path = os.path.join(folder_path, change['old'])
            new_path = os.path.join(folder_path, change['new'])
            
            # Проверяем валидность нового имени
            is_valid, error_msg = self.file_manager.validate_file_name(change['new'])
            if not is_valid:
                error_count += 1
                failed_files.append(f"{change['old']}: {error_msg}")
                continue
            
            # Проверяем, не существует ли уже файл с таким именем
            if os.path.exists(new_path) and new_path != old_path:
                error_count += 1
                failed_files.append(f"{change['old']}: файл '{change['new']}' уже существует")
                continue
            
            # Переименовываем файл
            success = self.file_manager.rename_file(old_path, change['new'], keep_original)
            
            if success:
                success_count += 1
            else:
                error_count += 1
                failed_files.append(f"{change['old']}: ошибка переименования")
        
        # После переименования перезагружаем файлы
        if success_count > 0:
            # Добавляем операцию в историю ТОЛЬКО если были успешные изменения
            # Используем changes_copy (изменения до переименования)
            successful_changes = []
            for change in changes_copy:
                old_path = os.path.join(folder_path, change['old'])
                new_path = os.path.join(folder_path, change['new'])
                # Проверяем, существует ли файл с новым именем (успешно переименован)
                if os.path.exists(new_path):
                    successful_changes.append(change)
            
            if successful_changes:
                self.undo_manager.add_operation(folder_path, successful_changes)
                self.undo_btn.setEnabled(True)
            
            # Перезагружаем файлы для обновления списка
            self.load_files()
        
        # Показываем результат
        self.progress_bar.setValue(100)
        
        if success_count > 0:
            self.status_label.setText(f"Успешно переименовано {success_count} файлов")
            
            if error_count > 0:
                QMessageBox.warning(
                    self, 
                    "Внимание", 
                    f"Успешно переименовано {success_count} файлов\n"
                    f"Не удалось переименовать {error_count} файлов\n\n"
                    "Подробности:\n" + "\n".join(failed_files[:10]) + 
                    ("\n..." if len(failed_files) > 10 else "")
                )
            else:
                QMessageBox.information(
                    self, 
                    "Успех", 
                    f"Успешно переименовано {success_count} файлов"
                )
        else:
            self.status_label.setText("Не удалось переименовать файлы")
            QMessageBox.critical(
                self, 
                "Ошибка", 
                f"Не удалось переименовать ни один файл:\n\n" + 
                "\n".join(failed_files[:10]) + 
                ("\n..." if len(failed_files) > 10 else "")
            )
            
    def undo_changes(self):
        # Откат последней операции
        # Проверяем, есть ли операции для отката
        if not self.undo_manager.has_operations():
            QMessageBox.information(self, "Информация", "Нет операций для отката")
            return
        
        last_op = self.undo_manager.get_last_operation()
        if not last_op:
            QMessageBox.information(self, "Информация", "Нет операций для отката")
            return
        
        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение отката",
            f"Откатить последнюю операцию переименования ({len(last_op.changes)} файлов)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Выполняем откат
        success = self.undo_manager.undo_last_operation()
        
        if success:
            # Обновляем интерфейс
            self.load_files()  # Перезагружаем файлы
            self.status_label.setText("Последняя операция отменена")
            
            # Обновляем состояние кнопки отката
            self.undo_btn.setEnabled(self.undo_manager.has_operations())
            
            QMessageBox.information(self, "Успех", "Операция успешно отменена")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось отменить операцию")
            
    def clear_rules(self):
        # Очистка правил и сброс предпросмотра
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Очистить все правила и сбросить предпросмотр?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Сбрасываем все чекбоксы включения
        self.enable_replace.setChecked(False)
        self.enable_prefix_suffix.setChecked(False)
        self.enable_numbering.setChecked(False)
        self.enable_exif.setChecked(False)
        
        # Сбрасываем поля ввода для замены текста
        self.replace_from.clear()
        self.replace_to.clear()
        self.simple_replace_mode.setChecked(True)  # Возвращаем к простому режиму
        self.case_sensitive.setChecked(False)
        self.replace_all.setChecked(True)
        self.regex_ignore_case.setChecked(False)
        self.regex_dotall.setChecked(False)
        
        # Сбрасываем другие поля
        self.prefix_text.clear()
        self.suffix_text.clear()
        self.suffix_before_ext.setChecked(True)
        
        self.start_number.setValue(1)
        self.digits_count.setValue(3)
        self.number_separator.setText("_")
        self.number_suffix.setChecked(True)
        
        self.date_format.setCurrentIndex(0)
        self.date_prefix.setChecked(True)
        self.exif_separator.setText("_")
        self.use_camera_model.setChecked(False)
        self.use_exposure.setChecked(False)
        self.use_gps.setChecked(False)
        
        self.lowercase_ext.setChecked(True)
        self.remove_spaces.setChecked(False)
        self.keep_original.setChecked(False)
        self.filter_extensions.clear()
        self.min_size.setValue(0)
        self.sort_by_name.setChecked(True)
        self.sort_asc.setChecked(True)
        
        # Сбрасываем таблицу к исходным именам (если есть файлы)
        if self.current_files:
            for i, filename in enumerate(self.current_files):
                if i < self.file_table.rowCount():
                    self.file_table.item(i, 2).setText(filename)
                    
                    status_item = self.file_table.item(i, 3)
                    status_item.setText("⏳ Ожидание")
                    status_item.setBackground(QColor("#fff9e6"))
                    status_item.setForeground(QColor("#f39c12"))
        
        self.preview_results.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Все правила очищены, предпросмотр сброшен")
        self.apply_btn.setEnabled(False)
        self.sort_btn.setEnabled(len(self.current_files) > 0)
        
        # Обновляем видимость групп параметров
        self.toggle_replace_mode()
