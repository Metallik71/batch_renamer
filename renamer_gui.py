# Графический интерфейс

import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QCheckBox, QRadioButton, QSpinBox,
    QComboBox, QTextEdit, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QHeaderView, QFormLayout, QButtonGroup, QFrame
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

class RenamerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        # Настройка пользовательского интерфейса
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
        # Создание секции выбора папки
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
        browse_btn.clicked.connect(self.dummy_browse)
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
        load_btn.clicked.connect(self.dummy_load)
        layout.addWidget(load_btn)
        
        group.setLayout(layout)
        return group
        
    def create_file_list_section(self):
        # Создание секции со списком файлов
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
        
        # Добавление демо-данных
        self.add_demo_data()
        
        layout.addWidget(self.file_table)
        return widget
        
    def add_demo_data(self):
        # Добавление демо-данных в таблицу
        demo_files = [
            ("IMG_20231201_001.jpg", "2023-12-01_photo_001.jpg", "✅ Изменено"),
            ("DSC_0456.JPG", "2023-11-15_vacation_002.jpg", "✅ Изменено"),
            ("document_old.pdf", "document_new.pdf", "✅ Изменено"),
            ("scan001.png", "scan001.png", "⏳ Ожидание"),
            ("IMG_1234.jpg", "IMG_1234.jpg", "⏳ Ожидание"),
            ("report_final.docx", "2023_report_final.docx", "✅ Изменено"),
            ("picture.png", "holiday_picture.png", "✅ Изменено"),
            ("data_backup.zip", "data_backup.zip", "⏳ Ожидание")
        ]
        
        self.file_table.setRowCount(len(demo_files))
        
        for i, (old_name, new_name, status) in enumerate(demo_files):
            # Номер
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
            self.file_table.setItem(i, 0, num_item)
            
            # Текущее имя
            old_item = QTableWidgetItem(old_name)
            old_item.setFlags(old_item.flags() & ~Qt.ItemIsEditable)
            self.file_table.setItem(i, 1, old_item)
            
            # Новое имя
            new_item = QTableWidgetItem(new_name)
            new_item.setFlags(new_item.flags() & ~Qt.ItemIsEditable)
            self.file_table.setItem(i, 2, new_item)
            
            # Статус
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            
            # Цветовая маркировка статуса
            if "Изменено" in status:
                status_item.setBackground(QColor("#d5f4e6"))
                status_item.setForeground(QColor("#27ae60"))
            else:
                status_item.setBackground(QColor("#fff9e6"))
                status_item.setForeground(QColor("#f39c12"))
                
            self.file_table.setItem(i, 3, status_item)
            
    def create_rules_section(self):
        #Создание секции с правилами переименования
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
        self.create_regex_tab()
        self.create_exif_tab()
        self.create_advanced_tab()
        
        layout.addWidget(self.tab_widget)
        return widget
        
    def create_text_replace_tab(self):
        #Вкладка 'Замена текста'
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Простая замена текста")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        
        form = QFormLayout()
        
        # Заменить
        self.replace_from = QLineEdit()
        self.replace_from.setPlaceholderText("Например: IMG_")
        form.addRow("Заменить:", self.replace_from)
        
        # На
        self.replace_to = QLineEdit()
        self.replace_to.setPlaceholderText("Например: Photo_")
        form.addRow("На:", self.replace_to)
        
        # Чекбоксы
        self.case_sensitive = QCheckBox("Учитывать регистр")
        self.replace_all = QCheckBox("Заменить все вхождения")
        self.replace_all.setChecked(True)
        
        form.addRow(self.case_sensitive)
        form.addRow(self.replace_all)
        
        # Пример
        example_label = QLabel("Пример: 'IMG_1234.jpg' → 'Photo_1234.jpg'")
        example_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        form.addRow(example_label)
        
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Замена")
        
    def create_prefix_suffix_tab(self):
        #Вкладка 'Префикс/Суффикс'
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Добавление префикса и/или суффикса")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        
        form = QFormLayout()
        
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
        suffix_layout = QVBoxLayout()
        
        self.suffix_before_ext = QRadioButton("Перед расширением (file_suffix.ext)")
        self.suffix_after_ext = QRadioButton("После расширения (file.ext_suffix)")
        self.suffix_before_ext.setChecked(True)
        
        suffix_layout.addWidget(self.suffix_before_ext)
        suffix_layout.addWidget(self.suffix_after_ext)
        suffix_group.setLayout(suffix_layout)
        
        form.addRow(suffix_group)
        
        # Пример
        example_label = QLabel("Пример: 'photo.jpg' → 'vacation_photo_edited.jpg'")
        example_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        form.addRow(example_label)
        
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Префикс/Суффикс")
        
    def create_numbering_tab(self):
        #Вкладка 'Нумерация'
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Параметры нумерации")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        
        form = QFormLayout()
        
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
        
    def create_regex_tab(self):
        #Вкладка 'Регулярные выражения'
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Регулярные выражения для сложных замен")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        
        form = QFormLayout()
        
        # Паттерн
        self.regex_pattern = QLineEdit()
        self.regex_pattern.setPlaceholderText(r"Например: (\d{4})-(\d{2})-(\d{2})")
        form.addRow("Регулярное выражение:", self.regex_pattern)
        
        # Замена
        self.regex_replacement = QLineEdit()
        self.regex_replacement.setPlaceholderText(r"Например: \3.\2.\1")
        form.addRow("Замена:", self.regex_replacement)
        
        # Чекбоксы
        self.regex_ignore_case = QCheckBox("Игнорировать регистр")
        self.regex_dotall = QCheckBox("Точка соответствует переводу строки")
        
        form.addRow(self.regex_ignore_case)
        form.addRow(self.regex_dotall)
        
        # Примеры
        examples_group = QGroupBox("Примеры использования")
        examples_layout = QVBoxLayout()
        
        examples = [
            "Формат даты: '2023-12-01' → '01.12.2023'",
            "Удаление пробелов: 'file name.jpg' → 'filename.jpg'",
            "Извлечение чисел: 'IMG_0456.jpg' → '0456.jpg'"
        ]
        
        for example in examples:
            label = QLabel(f"• {example}")
            label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
            examples_layout.addWidget(label)
            
        examples_group.setLayout(examples_layout)
        form.addRow(examples_group)
        
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Регулярки")
        
    def create_exif_tab(self):
        #Вкладка 'EXIF данные'
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = QGroupBox("Использование метаданных EXIF")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
        
        form = QFormLayout()
        
        # Включить EXIF
        self.use_exif = QCheckBox("Использовать дату съемки из EXIF")
        form.addRow(self.use_exif)
        
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
        self.date_suffix = QRadioButton("Суффикс")
        self.date_prefix.setChecked(True)
        
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
        extras_layout = QVBoxLayout()
        
        self.use_camera_model = QCheckBox("Модель камеры")
        self.use_exposure = QCheckBox("Параметры экспозиции")
        self.use_gps = QCheckBox("Координаты GPS")
        
        extras_layout.addWidget(self.use_camera_model)
        extras_layout.addWidget(self.use_exposure)
        extras_layout.addWidget(self.use_gps)
        exif_extras.setLayout(extras_layout)
        
        form.addRow(exif_extras)
        
        # Пример
        example_label = QLabel("Пример: 'IMG_1234.jpg' → '2023-12-01_1234.jpg'")
        example_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        form.addRow(example_label)
        
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "EXIF")
        
    def create_advanced_tab(self):
        #Вкладка 'Дополнительно'
        tab = QWidget()
        layout = QVBoxLayout(tab)
    
        # Группа 1: Расширения
        ext_group = QGroupBox("Обработка расширений файлов")
        ext_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
    
        ext_layout = QVBoxLayout()
    
        self.lowercase_ext = QCheckBox("Приводить расширения к нижнему регистру (.JPG → .jpg)")
        self.lowercase_ext.setChecked(True)
        self.remove_spaces = QCheckBox("Удалять пробелы в именах файлов")
        self.keep_original = QCheckBox("Сохранять копию оригинальных файлов")
    
        ext_layout.addWidget(self.lowercase_ext)
        ext_layout.addWidget(self.remove_spaces)
        ext_layout.addWidget(self.keep_original)
        ext_group.setLayout(ext_layout)
    
        # Группа 2: Фильтрация
        filter_group = QGroupBox("Фильтрация файлов")
        filter_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
    
        filter_layout = QFormLayout()

        self.filter_extensions = QLineEdit()
        self.filter_extensions.setPlaceholderText("jpg, png, pdf, docx (через запятую)")
        filter_layout.addRow("Расширения:", self.filter_extensions)
    
        self.min_size = QSpinBox()
        self.min_size.setSuffix(" KB")
        self.min_size.setRange(0, 100000)
        filter_layout.addRow("Минимальный размер:", self.min_size)
    
        filter_group.setLayout(filter_layout)
    
        # Группа 3: Сортировка
        sort_group = QGroupBox("Сортировка файлов перед переименованием")
        sort_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 15px;
            }
        """)
    
        sort_layout = QVBoxLayout()

        self.sort_by_name = QRadioButton("По имени")
        self.sort_by_date = QRadioButton("По дате создания")
        self.sort_by_size = QRadioButton("По размеру")
        self.sort_by_name.setChecked(True)
    
        sort_order_layout = QHBoxLayout()
        self.sort_asc = QRadioButton("По возрастанию")
        self.sort_desc = QRadioButton("По убыванию")
        self.sort_asc.setChecked(True)
    
        sort_order_layout.addWidget(self.sort_asc)
        sort_order_layout.addWidget(self.sort_desc)
    
        sort_layout.addWidget(self.sort_by_name)
        sort_layout.addWidget(self.sort_by_date)
        sort_layout.addWidget(self.sort_by_size)
        sort_layout.addLayout(sort_order_layout)
        sort_group.setLayout(sort_layout)
    
        layout.addWidget(ext_group)
        layout.addWidget(filter_group)
        layout.addWidget(sort_group)
        layout.addStretch()
    
        self.tab_widget.addTab(tab, "Дополнительно")
        
    def create_action_buttons(self):
        #Создание секции с кнопками действий
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
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
        preview_btn = QPushButton("👁️ Предпросмотр")
        preview_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        preview_btn.clicked.connect(self.dummy_preview)
        layout.addWidget(preview_btn)
        
        # Кнопка применения
        apply_btn = QPushButton("✅ Применить переименование")
        apply_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #2ecc71;
                color: white;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        apply_btn.clicked.connect(self.dummy_apply)
        layout.addWidget(apply_btn)
        
        # Кнопка отката
        undo_btn = QPushButton("↩️ Откатить последнюю операцию")
        undo_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        undo_btn.clicked.connect(self.dummy_undo)
        layout.addWidget(undo_btn)
        
        # Кнопка очистки
        clear_btn = QPushButton("🗑️ Очистить правила")
        clear_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #f39c12;
                color: white;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
        """)
        clear_btn.clicked.connect(self.dummy_clear)
        layout.addWidget(clear_btn)
        
        layout.addStretch()
        return widget
        
    def create_status_bar(self):
        #Создание статусной панели"
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
        
    def dummy_browse(self):
        #Заглушка для кнопки обзора
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.folder_path_edit.setText(folder)
            self.status_label.setText(f"Выбрана папка: {os.path.basename(folder)}")
            
    def dummy_load(self):
        #Заглушка для загрузки файлов
        if not self.folder_path_edit.text():
            QMessageBox.warning(self, "Внимание", "Сначала выберите папку!")
            return
            
        self.file_counter.setText("Файлов: 8")
        self.status_label.setText("Загружено 8 файлов для обработки")
        
    def dummy_preview(self):
        #Заглушка для предпросмотра
        self.progress_bar.setValue(50)
        self.status_label.setText("Предпросмотр выполнен. Проверьте изменения в таблице.")
        
    def dummy_apply(self):
        #Заглушка для применения
        reply = QMessageBox.question(self, "Подтверждение",
                                   "Вы уверены, что хотите переименовать 8 файлов?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.progress_bar.setValue(100)
            self.status_label.setText("Переименование успешно выполнено!")
            QMessageBox.information(self, "Успех", "Файлы успешно переименованы!")
            
    def dummy_undo(self):
        #Заглушка для отката
        reply = QMessageBox.question(self, "Откат",
                                   "Откатить последнюю операцию переименования?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.status_label.setText("Последняя операция отменена")
            
    def dummy_clear(self):
        #Заглушка для очистки
        self.folder_path_edit.clear()
        self.file_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.file_counter.setText("Файлов: 0")
        self.status_label.setText("Все правила очищены")