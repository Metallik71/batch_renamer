# Графический интерфейс 

import os
import re
import json
from typing import List, Dict, Any
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QMutex
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QCheckBox, QRadioButton, QSpinBox,
    QComboBox, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QHeaderView, QFormLayout, QButtonGroup, QTextEdit, 
    QSizePolicy, QDialog, QTreeWidget, QTreeWidgetItem, QStackedWidget,
    QScrollArea, QApplication, QMenu, QShortcut
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor, QKeySequence

# Импортируем модули
try:
    from file_manager import FileManager
    from rules_engine import RulesEngine
    from exif_processor import EXIFProcessor
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
        self._is_running = True  # Флаг для контроля выполнения
        
    def run(self):
        # Выполнение предпросмотра в фоновом потоке
        try:
            results = {}
            total_files = len(self.files)
            
            for i, file_name in enumerate(self.files):
                # Проверяем флаг перед выполнением следующей итерации
                if not self._is_running:
                    break
                    
                # Обновляем прогресс
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
                # Применяем правила - передаем индекс i для нумерации
                new_name = RulesEngine.generate_new_name(file_name, i, self.rules)
                
                # Применяем EXIF данные если нужно
                if self.rules.get('enable_exif', False):
                    file_path = os.path.join(self.folder_path, file_name)
                    
                    # Проверяем, является ли файл изображением и существует ли он
                    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', 
                                       '.bmp', '.gif', '.webp', '.heic', '.nef', 
                                       '.cr2', '.arw', '.dng'}
                    file_ext = os.path.splitext(file_name)[1].lower()
                    
                    if file_ext in image_extensions:
                        if os.path.exists(file_path):
                            try:
                                # Используем новый метод из EXIFProcessor
                                template = self.rules.get('exif_template', '{date}_{camera}')
                                exif_name = EXIFProcessor.generate_filename_from_exif(
                                    new_name, file_path, template
                                )
                                
                                # Применяем дополнительные настройки
                                if self.rules.get('clean_exif_names', True):
                                    exif_name = EXIFProcessor.clean_for_filename(exif_name)
                                
                                if self.rules.get('exif_lowercase', False):
                                    name_part, ext = os.path.splitext(exif_name)
                                    exif_name = name_part.lower() + ext
                                
                                if self.rules.get('exif_replace_spaces', True):
                                    exif_name = exif_name.replace(' ', '_')
                                
                                new_name = exif_name
                            except Exception as e:
                                # Если ошибка при чтении EXIF, оставляем имя без изменений
                                print(f"Ошибка при обработке EXIF для файла {file_name}: {e}")
                        else:
                            print(f"Файл не существует: {file_path}")
                    else:
                        # Не изображение - оставляем имя без изменений
                        pass
                
                results[file_name] = new_name
            
            if self._is_running:  # Отправляем результаты только если не прервали
                self.preview_finished.emit(results)
            
        except Exception as e:
            if self._is_running:  # Отправляем ошибку только если не прервали
                self.error_occurred.emit(str(e))
    
    def stop(self):
        """Безопасная остановка потока"""
        self._is_running = False
        self.quit()
        if not self.wait(2000):  # Ждем до 2 секунд для завершения
            print("Предупреждение: поток не завершился вовремя")
            self.terminate()  # Принудительное завершение


class EXIFPreviewDialog(QDialog):
    """Диалог для просмотра EXIF данных с безопасным закрытием"""
    
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.exif_data = {}
        self.is_closing = False  # Флаг для предотвращения повторного закрытия
        self.setWindowTitle(f"EXIF данные: {os.path.basename(file_path)}")
        self.setGeometry(300, 300, 800, 700)
        self.setup_ui()
        
        # Используем таймер для отложенной загрузки данных
        QTimer.singleShot(50, self.safe_load_exif_data)
    
    def safe_load_exif_data(self):
        """Безопасная загрузка EXIF данных"""
        if self.is_closing:
            return
            
        try:
            self.load_exif_data()
        except Exception as e:
            if not self.is_closing:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить EXIF данные:\n{str(e)}")
            self.force_close()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        header = QHBoxLayout()
        title = QLabel(f"📷 EXIF данные: {os.path.basename(self.file_path)}")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        
        # Кнопка обновления
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("Обновить данные")
        refresh_btn.clicked.connect(lambda: QTimer.singleShot(10, self.safe_load_exif_data))
        refresh_btn.setFixedSize(30, 30)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # Вкладки
        self.tabs = QTabWidget()
        
        # Вкладка 1: Быстрый просмотр
        self.quick_tab = QWidget()
        self.quick_layout = QVBoxLayout(self.quick_tab)
        
        # Сводная информация
        summary_group = QGroupBox("📊 Сводная информация")
        summary_layout = QFormLayout(summary_group)
        
        self.summary_labels = {
            'camera': QLabel(""),
            'date': QLabel(""),
            'lens': QLabel(""),
            'exposure': QLabel(""),
            'dimensions': QLabel(""),
            'has_exif': QLabel("")
        }
        
        summary_layout.addRow("Камера:", self.summary_labels['camera'])
        summary_layout.addRow("Дата съемки:", self.summary_labels['date'])
        summary_layout.addRow("Объектив:", self.summary_labels['lens'])
        summary_layout.addRow("Экспозиция:", self.summary_labels['exposure'])
        summary_layout.addRow("Разрешение:", self.summary_labels['dimensions'])
        summary_layout.addRow("Статус:", self.summary_labels['has_exif'])
        
        self.quick_layout.addWidget(summary_group)
        
        # Шаблон
        template_group = QGroupBox("🏷️ Быстрый шаблон имени")
        template_layout = QVBoxLayout(template_group)
        
        self.template_input = QLineEdit()
        self.template_input.setText("{date}_{camera}_{focal}mm_F{aperture}_ISO{iso}")
        self.template_input.textChanged.connect(self.update_preview)
        template_layout.addWidget(QLabel("Шаблон:"))
        template_layout.addWidget(self.template_input)
        
        # Быстрые пресеты
        presets_layout = QHBoxLayout()
        
        presets = [
            ("📅 Только дата", "{date}"),
            ("📸 Дата+Камера", "{date}_{camera}"),
            ("⚙️ Параметры", "{date}_{focal}mm_F{aperture}_ISO{iso}"),
            ("🎯 Полный", "{date}_{camera}_{focal}mm_F{aperture}_{shutter}_ISO{iso}")
        ]
        
        for name, template in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, t=template: self.set_template(t))
            presets_layout.addWidget(btn)
        
        template_layout.addLayout(presets_layout)
        
        # Предпросмотр
        preview_box = QGroupBox("👁️ Предпросмотр имени файла")
        preview_layout = QVBoxLayout(preview_box)
        
        self.preview_label = QLabel("Загрузка...")
        self.preview_label.setStyleSheet("""
            QLabel {
                padding: 15px;
                background: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                color: #495057;
                font-family: monospace;
                font-size: 12px;
                min-height: 80px;
            }
        """)
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        
        template_layout.addWidget(preview_box)
        self.quick_layout.addWidget(template_group)
        self.quick_layout.addStretch()
        
        # Вкладка 2: Структурированный просмотр
        self.tree_tab = QWidget()
        tree_layout = QVBoxLayout(self.tree_tab)
        
        self.exif_tree = QTreeWidget()
        self.exif_tree.setHeaderLabels(["Тег", "Значение"])
        self.exif_tree.setColumnWidth(0, 250)
        self.exif_tree.setColumnWidth(1, 400)
        tree_layout.addWidget(self.exif_tree)
        
        # Вкладка 3: Сырые данные
        self.raw_tab = QWidget()
        raw_layout = QVBoxLayout(self.raw_tab)
        
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setFont(QFont("Courier", 9))
        raw_layout.addWidget(self.raw_text)
        
        # Вкладка 4: Доступные плейсхолдеры
        self.placeholders_tab = QWidget()
        placeholders_layout = QVBoxLayout(self.placeholders_tab)
        
        placeholders_group = QGroupBox("📝 Доступные плейсхолдеры")
        placeholders_inner = QVBoxLayout(placeholders_group)
        
        self.placeholder_text = QTextEdit()
        self.placeholder_text.setReadOnly(True)
        self.placeholder_text.setFont(QFont("Courier", 9))
        
        # Формируем список плейсхолдеров
        placeholders_info = "Доступные плейсхолдеры для шаблонов:\n"
        placeholders_info += "=" * 50 + "\n"
        
        for placeholder, description in EXIFProcessor.get_supported_placeholders().items():
            placeholders_info += f"{placeholder:<20} - {description}\n"
        
        placeholders_info += "\nПримеры шаблонов:\n"
        placeholders_info += "- {date}_{camera}_{iso}\n"
        placeholders_info += "- {date}_{time}_{focal}mm_F{aperture}\n"
        placeholders_info += "- {camera}_{datetime}_{lens}\n"
        
        self.placeholder_text.setText(placeholders_info)
        placeholders_inner.addWidget(self.placeholder_text)
        
        placeholders_layout.addWidget(placeholders_group)
        placeholders_layout.addStretch()
        
        # Добавляем вкладки
        self.tabs.addTab(self.quick_tab, "⚡ Быстрый просмотр")
        self.tabs.addTab(self.tree_tab, "📊 Структура")
        self.tabs.addTab(self.raw_tab, "📄 Сырые данные")
        self.tabs.addTab(self.placeholders_tab, "❓ Плейсхолдеры")
        
        layout.addWidget(self.tabs)
        
        # Кнопки
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        self.copy_template_btn = QPushButton("📋 Копировать шаблон")
        self.copy_template_btn.clicked.connect(self.safe_copy_template)
        buttons.addWidget(self.copy_template_btn)
        
        self.copy_exif_btn = QPushButton("📋 Копировать EXIF")
        self.copy_exif_btn.clicked.connect(self.safe_copy_exif_data)
        buttons.addWidget(self.copy_exif_btn)
        
        self.apply_btn = QPushButton("✅ Использовать шаблон")
        self.apply_btn.clicked.connect(self.safe_use_template)
        self.apply_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        buttons.addWidget(self.apply_btn)
        
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.safe_close)
        buttons.addWidget(self.close_btn)
        
        layout.addLayout(buttons)
    
    def load_exif_data(self):
        """Загрузка EXIF данных"""
        try:
            if self.is_closing:
                return
                
            # Проверяем существование файла
            if not os.path.exists(self.file_path):
                if not self.is_closing:
                    QMessageBox.critical(self, "Ошибка", f"Файл не существует:\n{self.file_path}")
                self.force_close()
                return
            
            # Проверяем, что это файл (а не папка)
            if not os.path.isfile(self.file_path):
                if not self.is_closing:
                    QMessageBox.critical(self, "Ошибка", f"Путь указывает на папку, а не на файл:\n{self.file_path}")
                self.force_close()
                return
            
            self.exif_data = EXIFProcessor.get_all_exif_data(self.file_path)
            
            if not self.exif_data:
                self.show_no_exif_message()
                return
            
            # Обновляем сводную информацию
            self.update_summary_info()
            
            # Заполняем дерево
            self.exif_tree.clear()
            
            # Группируем по категориям
            categories = {
                "📅 Дата и время": ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized', 'SubSecTime'],
                "📸 Камера": ['Make', 'Model', 'BodySerialNumber', 'Software', 'Artist', 'Copyright'],
                "🔍 Объектив": ['LensModel', 'LensMake', 'LensSerialNumber', 'FocalLength', 
                               'FocalLengthIn35mmFilm', 'MaxApertureValue'],
                "⚙️ Экспозиция": ['ExposureTime', 'FNumber', 'ExposureProgram', 'ISOSpeedRatings', 
                                 'ExposureBiasValue', 'MeteringMode', 'Flash', 'LightSource',
                                 'WhiteBalance', 'SceneCaptureType'],
                "📐 Изображение": ['ImageWidth', 'ImageHeight', 'XResolution', 'YResolution',
                                 'ResolutionUnit', 'ColorSpace', 'Orientation', 'BitsPerSample'],
                "📍 GPS": ['GPSInfo'],
                "🏷️ Другое": ['ImageDescription', 'Rating', 'Keywords', 'Subject']
            }
            
            for category, tags in categories.items():
                category_item = QTreeWidgetItem(self.exif_tree, [category, ""])
                category_item.setExpanded(True)
                
                for tag in tags:
                    if tag in self.exif_data:
                        value = self.exif_data[tag]
                        formatted = EXIFProcessor.format_exif_value(tag, value)
                        item = QTreeWidgetItem(category_item, [tag, formatted])
            
            # Сырые данные
            try:
                raw_text = json.dumps(self.exif_data, indent=2, default=str)
                self.raw_text.setPlainText(raw_text)
            except:
                self.raw_text.setPlainText("Не удалось преобразовать в JSON")
            
            # Обновляем предпросмотр
            self.update_preview()
            
        except Exception as e:
            if not self.is_closing:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить EXIF данные:\n{str(e)}")
                self.force_close()
    
    def show_no_exif_message(self):
        """Показать сообщение об отсутствии EXIF"""
        self.summary_labels['has_exif'].setText("❌ Нет EXIF данных")
        self.summary_labels['has_exif'].setStyleSheet("color: #dc3545; font-weight: bold;")
        
        self.exif_tree.clear()
        no_data_item = QTreeWidgetItem(self.exif_tree, ["Нет данных", "Файл не содержит EXIF метаданных"])
        no_data_item.setForeground(0, QColor("#6c757d"))
        
        self.raw_text.setPlainText("Файл не содержит EXIF метаданных.")
        self.preview_label.setText("❌ Файл не содержит EXIF данных для генерации имени")
    
    def update_summary_info(self):
        """Обновление сводной информации"""
        try:
            summary = EXIFProcessor.get_exif_summary(self.file_path)
            
            if summary.get('has_exif'):
                self.summary_labels['has_exif'].setText("✅ Есть EXIF данные")
                self.summary_labels['has_exif'].setStyleSheet("color: #28a745; font-weight: bold;")
                
                self.summary_labels['camera'].setText(f"{summary.get('make', '')} {summary.get('camera', '')}")
                self.summary_labels['date'].setText(f"{summary.get('date', '')} {summary.get('time', '')}")
                self.summary_labels['lens'].setText(summary.get('lens', 'Неизвестно'))
                
                exposure_parts = []
                if summary.get('aperture'):
                    exposure_parts.append(summary['aperture'])
                if summary.get('shutter_speed'):
                    exposure_parts.append(summary['shutter_speed'])
                if summary.get('iso'):
                    exposure_parts.append(summary['iso'])
                
                self.summary_labels['exposure'].setText(" ".join(exposure_parts) if exposure_parts else "Неизвестно")
                self.summary_labels['dimensions'].setText(summary.get('dimensions', 'Неизвестно'))
            else:
                self.summary_labels['has_exif'].setText("❌ Нет EXIF данных")
                self.summary_labels['has_exif'].setStyleSheet("color: #dc3545; font-weight: bold;")
        except Exception as e:
            print(f"Ошибка при обновлении сводной информации: {e}")
            self.summary_labels['has_exif'].setText("❌ Ошибка при загрузке данных")
    
    def update_preview(self):
        """Обновление предпросмотра имени"""
        try:
            if not self.exif_data:
                self.preview_label.setText("❌ Нет EXIF данных для генерации имени")
                return
            
            template = self.template_input.text()
            original = os.path.basename(self.file_path)
            
            # Проверяем шаблон
            is_valid, error_msg = EXIFProcessor.validate_template(template)
            if not is_valid:
                self.preview_label.setText(f"⚠️ Ошибка в шаблоне: {error_msg}")
                return
            
            # Генерируем новое имя
            new_name = EXIFProcessor.generate_filename_from_exif(original, self.file_path, template)
            
            if new_name == original:
                self.preview_label.setText("ℹ️ Имя не изменится (нет данных для подстановки)")
            else:
                self.preview_label.setText(f"{original}\n↓\n{new_name}")
            
        except Exception as e:
            self.preview_label.setText(f"⚠️ Ошибка: {str(e)}")
    
    def set_template(self, template: str):
        """Установить шаблон"""
        self.template_input.setText(template)
    
    def safe_copy_template(self):
        """Безопасное копирование шаблона в буфер"""
        if self.is_closing:
            return
            
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.template_input.text())
            QMessageBox.information(self, "Скопировано", "Шаблон скопирован в буфер обмена")
        except Exception as e:
            if not self.is_closing:
                QMessageBox.warning(self, "Ошибка", f"Не удалось скопировать шаблон:\n{str(e)}")
    
    def safe_copy_exif_data(self):
        """Безопасное копирование EXIF данных в буфер"""
        if self.is_closing:
            return
            
        try:
            clipboard = QApplication.clipboard()
            
            # Формируем текстовое представление
            exif_text = f"EXIF данные: {os.path.basename(self.file_path)}\n"
            exif_text += "=" * 50 + "\n\n"
            
            if self.exif_data:
                for key, value in self.exif_data.items():
                    try:
                        formatted = EXIFProcessor.format_exif_value(key, value)
                        exif_text += f"{key}: {formatted}\n"
                    except:
                        exif_text += f"{key}: {value}\n"
            else:
                exif_text += "Нет EXIF данных"
            
            clipboard.setText(exif_text)
            QMessageBox.information(self, "Скопировано", "EXIF данные скопированы в буфер обмена")
        except Exception as e:
            if not self.is_closing:
                QMessageBox.warning(self, "Ошибка", f"Не удалось скопировать EXIF данные:\n{str(e)}")
    
    def safe_use_template(self):
        """Безопасное использование шаблона в основном окне"""
        if self.is_closing:
            return
            
        template = self.template_input.text()
        
        try:
            # Ищем родительское окно RenamerWindow
            parent = self.parent()
            while parent and not isinstance(parent, RenamerWindow):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'exif_widget'):
                try:
                    # Включаем EXIF если выключен
                    if not parent.exif_widget.enable_exif.isChecked():
                        parent.exif_widget.enable_exif.setChecked(True)
                    
                    # Устанавливаем шаблон
                    parent.exif_widget.set_template(template)
                    
                    if not self.is_closing:
                        QMessageBox.information(
                            self,
                            "Шаблон установлен",
                            "Шаблон EXIF установлен в основном окне.\n"
                            "Теперь вы можете применить его ко всем файлам."
                        )
                except Exception as e:
                    if not self.is_closing:
                        QMessageBox.warning(self, "Ошибка", f"Не удалось установить шаблон:\n{str(e)}")
            
            self.accept()
        except Exception as e:
            if not self.is_closing:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при использовании шаблона:\n{str(e)}")
    
    def safe_close(self):
        """Безопасное закрытие диалога"""
        if not self.is_closing:
            self.accept()
    
    def force_close(self):
        """Принудительное закрытие диалога"""
        self.is_closing = True
        try:
            self.reject()
        except:
            try:
                self.close()
            except:
                pass
    
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        self.is_closing = True
        event.accept()


class EXIFTemplateWidget(QWidget):
    """Виджет для работы с EXIF шаблонами (встраивается в основное окне)"""
    
    template_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Включение EXIF
        self.enable_exif = QCheckBox("🏷️ Использовать EXIF для именования")
        self.enable_exif.setChecked(False)
        self.enable_exif.stateChanged.connect(self.on_toggle)
        layout.addWidget(self.enable_exif)
        
        # Контейнер для настроек (скрыт по умолчанию)
        self.settings_container = QWidget()
        settings_layout = QVBoxLayout(self.settings_container)
        settings_layout.setContentsMargins(20, 10, 0, 0)
        
        # Шаблон
        template_group = QGroupBox("Шаблон имени из EXIF")
        template_layout = QVBoxLayout(template_group)
        
        self.template_input = QLineEdit()
        self.template_input.setText("{date}_{time}_{camera}_{focal}mm_F{aperture}_ISO{iso}")
        self.template_input.textChanged.connect(self.on_template_change)
        template_layout.addWidget(QLabel("Шаблон:"))
        template_layout.addWidget(self.template_input)
        
        # Предпросмотр
        self.preview_label = QLabel("Пример: 2023-12-01_14-30_Canon_50mm_F2.8_ISO100.jpg")
        self.preview_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                color: #6c757d;
                font-size: 11px;
            }
        """)
        self.preview_label.setWordWrap(True)
        template_layout.addWidget(QLabel("Пример:"))
        template_layout.addWidget(self.preview_label)
        
        # Быстрые кнопки
        buttons_layout = QHBoxLayout()
        
        presets = [
            ("📅 Только дата", "{date}"),
            ("📸 Дата+Камера", "{date}_{camera}"),
            ("⚙️ Параметры", "{date}_{focal}mm_F{aperture}_ISO{iso}"),
            ("🎯 Подробно", "{date}_{time}_{camera}_{focal}mm_F{aperture}_{shutter}_ISO{iso}")
        ]
        
        for name, template in presets:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 10px;
                    padding: 3px 6px;
                }
            """)
            btn.clicked.connect(lambda checked, t=template: self.set_template(t))
            buttons_layout.addWidget(btn)
        
        template_layout.addLayout(buttons_layout)
        settings_layout.addWidget(template_group)
        
        # Дополнительные опции
        options_group = QGroupBox("Дополнительные настройки")
        options_layout = QVBoxLayout(options_group)
        
        self.clean_names = QCheckBox("Очищать названия (удалять спецсимволы)")
        self.clean_names.setChecked(True)
        options_layout.addWidget(self.clean_names)
        
        self.lowercase = QCheckBox("Приводить к нижнему регистру")
        self.lowercase.setChecked(False)
        options_layout.addWidget(self.lowercase)
        
        self.replace_spaces = QCheckBox("Заменять пробелы на '_'")
        self.replace_spaces.setChecked(True)
        options_layout.addWidget(self.replace_spaces)
        
        settings_layout.addWidget(options_group)
        
        # Кнопка просмотра EXIF
        view_btn = QPushButton("👁️ Просмотреть EXIF данных выбранного файла")
        view_btn.clicked.connect(self.show_exif_viewer)
        view_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        settings_layout.addWidget(view_btn)
        
        settings_layout.addStretch()
        
        layout.addWidget(self.settings_container)
        
        # Изначально скрываем настройки
        self.settings_container.setVisible(False)
    
    def on_toggle(self):
        """Включение/выключение EXIF"""
        enabled = self.enable_exif.isChecked()
        self.settings_container.setVisible(enabled)
        self.template_changed.emit(self.template_input.text() if enabled else "")
    
    def on_template_change(self):
        """Изменение шаблона"""
        if self.enable_exif.isChecked():
            self.template_changed.emit(self.template_input.text())
    
    def set_template(self, template: str):
        """Установить шаблон"""
        self.template_input.setText(template)
        self.on_template_change()
    
    def show_exif_viewer(self):
        """Показать просмотрщик EXIF"""
        # Этот метод будет вызываться из основного окна
        if hasattr(self.parent(), 'show_exif_for_selected'):
            self.parent().show_exif_for_selected()
    
    def get_rules(self) -> dict:
        """Получить правила EXIF"""
        return {
            'enable_exif': self.enable_exif.isChecked(),
            'exif_template': self.template_input.text(),
            'clean_exif_names': self.clean_names.isChecked(),
            'exif_lowercase': self.lowercase.isChecked(),
            'exif_replace_spaces': self.replace_spaces.isChecked()
        }
    
    def set_rules(self, rules: dict):
        """Установить правила EXIF"""
        self.enable_exif.setChecked(rules.get('enable_exif', False))
        self.template_input.setText(rules.get('exif_template', '{date}_{camera}'))
        self.clean_names.setChecked(rules.get('clean_exif_names', True))
        self.lowercase.setChecked(rules.get('exif_lowercase', False))
        self.replace_spaces.setChecked(rules.get('exif_replace_spaces', True))
        self.on_toggle()


class HelpWidget(QWidget):
    """Виджет со справочной информацией"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        title = QLabel("📚 Руководство пользователя")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; padding: 10px 0;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Scroll Area для длинного текста
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f9f9fa;
            }
        """)
        
        # Контейнер для контента
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)
        
        # Разделы помощи
        self.create_section(content_layout, "🎯 Назначение программы", 
                           "Программа позволяет массово переименовывать файлы с использованием различных правил и шаблонов.")
        
        # Текст помощи
        help_text = self.create_help_text()
        self.create_section(content_layout, "📌 Основные возможности", help_text)
        
        # Быстрые подсказки
        self.create_tips_section(content_layout)
        
        # Примеры
        self.create_examples_section(content_layout)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_help)
        layout.addWidget(refresh_btn)
    
    def create_section(self, layout, title_text, content):
        """Создание раздела справки"""
        section = QGroupBox(title_text)
        section.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #3498db;
                border-radius: 5px;
                margin-top: 5px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
            }
        """)
        
        section_layout = QVBoxLayout(section)
        
        if isinstance(content, str):
            label = QLabel(content)
            label.setWordWrap(True)
            label.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    line-height: 1.4;
                    color: #34495e;
                }
            """)
            section_layout.addWidget(label)
        else:
            section_layout.addWidget(content)
        
        layout.addWidget(section)
    
    def create_help_text(self):
        """Создание текстового содержимого справки"""
        help_html = """
        <style>
            .section { margin-bottom: 20px; }
            .title { font-size: 13px; font-weight: bold; color: #2c3e50; margin-top: 15px; }
            .subtitle { font-size: 12px; font-weight: bold; color: #3498db; margin-top: 10px; }
            .content { font-size: 11px; color: #34495e; margin-left: 10px; line-height: 1.4; }
            .example { background-color: #f8f9fa; padding: 8px; border-left: 3px solid #3498db; margin: 5px 0; }
            .tip { background-color: #e8f4fc; padding: 8px; border-radius: 4px; margin: 5px 0; }
            .warning { background-color: #fde8e8; padding: 8px; border-radius: 4px; margin: 5px 0; }
            code { background-color: #ecf0f1; padding: 2px 4px; border-radius: 3px; font-family: monospace; }
        </style>
        
        <div class="section">
            <div class="title">1. Базовые операции</div>
            <div class="content">
                <div class="subtitle">Замена текста</div>
                <div class="content">Простой поиск и замена текста в именах файлов</div>
                
                <div class="subtitle">Префикс/суффикс</div>
                <div class="content">Добавление текста в начало или конец имени файла</div>
                
                <div class="subtitle">Нумерация</div>
                <div class="content">Добавление порядковых номеров к файлам</div>
                
                <div class="subtitle">EXIF данные</div>
                <div class="content">Использование метаданных фотографий для именования</div>
            </div>
        </div>
        
        <div class="section">
            <div class="title">2. Расширенные функции</div>
            <div class="content">
                • <b>Регулярные выражения</b> - сложные шаблоны замены<br>
                • <b>Фильтрация файлов</b> - по расширениям и размеру<br>
                • <b>Сортировка</b> - по имени, дате, размеру<br>
                • <b>Резервные копии</b> - сохранение оригиналов<br>
                • <b>Откат операций</b> - возврат последнего переименования
            </div>
        </div>
        
        <div class="section">
            <div class="title">3. EXIF плейсхолдеры</div>
            <div class="content">
                <div class="example">
                    <code>{date}</code> - дата съемки (2024-01-15)<br>
                    <code>{camera}</code> - модель камеры<br>
                    <code>{focal}</code> - фокусное расстояние<br>
                    <code>{iso}</code> - значение ISO<br>
                    <code>{aperture}</code> - диафрагма<br>
                    <code>{shutter}</code> - выдержка<br>
                    <code>{lens}</code> - модель объектива
                </div>
                <div class="tip">
                    <b>Пример шаблона:</b> <code>{date}_{camera}_{focal}mm_F{aperture}_ISO{iso}</code><br>
                    <b>Результат:</b> <code>2024-01-15_Canon_50mm_F2.8_ISO100.jpg</code>
                </div>
            </div>
        </div>
        """
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(help_html)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                font-size: 11px;
            }
        """)
        return text_edit
    
    def create_tips_section(self, layout):
        """Создание раздела с подсказками"""
        tips_widget = QWidget()
        tips_layout = QVBoxLayout(tips_widget)
        tips_layout.setSpacing(5)
        
        tips = [
            ("✅ Всегда проверяйте предпросмотр перед применением", "#d4edda"),
            ("📸 EXIF работает только с изображениями", "#d1ecf1"),
            ("💾 Включайте резервные копии для важных файлов", "#fff3cd"),
            ("🔄 Используйте откат если что-то пошло не так", "#f8d7da"),
            ("🔍 Регулярные выражения требуют проверки синтаксиса", "#e2e3e5")
        ]
        
        for tip, color in tips:
            tip_label = QLabel(tip)
            tip_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    padding: 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    border-left: 4px solid #6c757d;
                }}
            """)
            tip_label.setWordWrap(True)
            tips_layout.addWidget(tip_label)
        
        self.create_section(layout, "💡 Быстрые подсказки", tips_widget)
    
    def create_examples_section(self, layout):
        """Создание раздела с примерами"""
        examples_html = """
        <table border="0" cellpadding="5" cellspacing="0" style="width:100%;">
            <tr style="background-color:#f8f9fa;">
                <th style="text-align:left; padding:8px;">Задача</th>
                <th style="text-align:left; padding:8px;">Настройки</th>
                <th style="text-align:left; padding:8px;">Результат</th>
            </tr>
            <tr>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">Нумерация фото</td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">Нумерация: вкл, 3 цифры, с 1</td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;"><code>photo_001.jpg</code></td>
            </tr>
            <tr>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">Добавить дату</td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">Префикс: <code>2024-01-15_</code></td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;"><code>2024-01-15_document.pdf</code></td>
            </tr>
            <tr>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">EXIF именование</td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;">EXIF: вкл, шаблон <code>{date}_{camera}</code></td>
                <td style="padding:8px; border-bottom:1px solid #dee2e6;"><code>2024-01-15_Canon.jpg</code></td>
            </tr>
            <tr>
                <td style="padding:8px;">Замена текста</td>
                <td style="padding:8px;">Замена: <code>IMG_</code> → <code>Photo_</code></td>
                <td style="padding:8px;"><code>Photo_1234.jpg</code></td>
            </tr>
        </table>
        """
        
        examples_edit = QTextEdit()
        examples_edit.setReadOnly(True)
        examples_edit.setHtml(examples_html)
        examples_edit.setMaximumHeight(200)
        
        self.create_section(layout, "🎯 Примеры использования", examples_edit)
    
    def refresh_help(self):
        """Обновление справки"""
        QMessageBox.information(self, "Обновлено", "Справка обновлена")


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
        
        self.worker = None  # Добавляем ссылку на текущий воркер
        
        self.setup_ui()
        QTimer.singleShot(0, self.initialize_disabled_fields)
        self.setup_shortcuts()
        
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        print("Закрытие приложения...")
        
        # Останавливаем все активные потоки
        if self.worker and self.worker.isRunning():
            print("Останавливаем воркер перед закрытием...")
            self.worker.stop()
            
            # Даем время потоку завершиться
            import time
            start_time = time.time()
            while self.worker.isRunning() and time.time() - start_time < 3:
                QApplication.processEvents()  # Обрабатываем события
                time.sleep(0.1)
            
            if self.worker.isRunning():
                print("Воркер все еще работает, принудительно завершаем")
                self.worker.terminate()
                self.worker.wait(1000)
        
        # Закрываем все дочерние окна
        for widget in QApplication.topLevelWidgets():
            if widget != self and isinstance(widget, QDialog):
                widget.close()
                widget.deleteLater()
        
        # Очищаем ресурсы
        QApplication.processEvents()
        
        event.accept()
        print("Приложение закрыто")
    
    def initialize_disabled_fields(self):
        """Инициализация всех полей как отключенных при запуске"""
        self.toggle_replace_fields()
        self.toggle_replace_mode()
        self.toggle_prefix_suffix_fields()
        self.toggle_numbering_fields()
        
        # Инициализируем EXIF виджет
        if hasattr(self, 'exif_widget'):
            self.exif_widget.settings_container.setVisible(False)
        
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
        
        # Подключаем двойной клик по таблице
        self.file_table.itemDoubleClicked.connect(self.on_file_double_clicked)
        
        # Добавляем контекстное меню
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.show_table_context_menu)
        
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
        self.create_help_tab()

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
        self.enable_replace = QCheckBox("Включить замены текста")
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
        # Уменьшаем расстояние между заголовками и полей ввода
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
        """Вкладка 'EXIF данные' с новым виджетом"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Создаем EXIF виджет
        self.exif_widget = EXIFTemplateWidget()
        self.exif_widget.template_changed.connect(self.on_exif_template_changed)
        layout.addWidget(self.exif_widget)
        
        # Информация
        info_label = QLabel("ℹ️ EXIF данные используются только для изображений (JPG, PNG, TIFF и др.)")
        info_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-style: italic;
                font-size: 11px;
                padding: 5px;
                margin-top: 10px;
                border-top: 1px solid #dee2e6;
            }
        """)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "EXIF")
    
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

    def create_help_tab(self):
        """Вкладка 'Помощь' со справочной информацией"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
    
        # Создаем виджет помощи
        self.help_widget = HelpWidget()
        layout.addWidget(self.help_widget)
    
        # Кнопки быстрого доступа
        quick_buttons = self.create_quick_help_buttons()
        layout.addWidget(quick_buttons)
    
        self.tab_widget.addTab(tab, "❓ Помощь")
    
    def create_quick_help_buttons(self):
        """Создание панели с кнопками быстрой помощи"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
        buttons_info = [
            ("📚 Полное руководство", self.show_full_manual),
            ("🎯 Примеры", self.show_examples),
            ("⚡ Быстрый старт", self.show_quick_start),
            ("❓ Частые вопросы", self.show_faq)
        ]
        
        for text, callback in buttons_info:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 12px;
                    background-color: #6c757d;
                    color: white;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        layout.addStretch()
        return widget

    def show_full_manual(self):
        """Показать полное руководство"""
        QMessageBox.information(self, "Полное руководство", 
            "Полное руководство доступно во вкладке 'Помощь'.\n\n"
            "Здесь вы найдете:\n"
            "• Подробное описание всех функций\n"
            "• Примеры использования\n"
            "• Советы и рекомендации\n"
            "• Ответы на частые вопросы")
    
    def show_examples(self):
        """Показать примеры использования"""
        examples = """
        📸 <b>Примеры переименования:</b>
        
        <u>Для фотографий:</u>
        • {date}_{camera}_{iso} → 2024-01-15_Canon_ISO100.jpg
        • {date}_{time}_{focal}mm → 2024-01-15_14-30_50mm.jpg
        
        <u>Для документов:</u>
        • Префикс + нумерация → report_001.pdf
        • Год_месяц_название → 2024_01_budget.xlsx
        
        <u>Простые замены:</u>
        • DSC_ → Photo_ (замена префикса)
        • _ → - (замена символов)
        • Удаление пробелов
        """
        
        QMessageBox.information(self, "Примеры использования", examples)
    
    def show_quick_start(self):
        """Показать быстрый старт"""
        quick_start = """
        🚀 <b>Быстрый старт:</b>
        
        1. Выберите папку с файлами
        2. Загрузите файлы (кнопка 📥)
        3. Настройте правила переименования
        4. Нажмите 👁️ Предпросмотр
        5. Примените изменения ✅
        
        <u>Базовые правила:</u>
        • Префикс/суффикс - добавляет текст
        • Нумерация - порядковые номера
        • Замена текста - поиск и замена
        • EXIF - данные из фотографий
        
        <u>Важно:</u>
        • Всегда проверяйте предпросмотр!
        • Используйте резервные копии
        """
        
        QMessageBox.information(self, "Быстрый старт", quick_start)
    
    def show_faq(self):
        """Показать частые вопросы"""
        faq = """
        ❓ <b>Частые вопросы:</b>
        
        <u>1. Почему EXIF не работает?</u>
        • Файл не является изображением
        • В изображении нет EXIF данных
        • Проверьте расширение файла
        
        <u>2. Как отменить переименование?</u>
        • Используйте кнопку ↩️ Откатить
        • Работает только для последней операции
        
        <u>3. Почему файлы не загружаются?</u>
        • Проверьте фильтры (расширения, размер)
        • Убедитесь что в папке есть файлы
        
        <u>4. Как использовать регулярные выражения?</u>
        • Включите режим "Регулярные выражения"
        • Проверяйте синтаксис в предпросмотре
        """
        
        QMessageBox.information(self, "Частые вопросы", faq)
        
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
            
            # Применяем фильтрация по размеру
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
            
            # Дополнительно
            'lowercase_ext': self.lowercase_ext.isChecked(),
            'remove_spaces': self.remove_spaces.isChecked(),
            'keep_original': self.keep_original.isChecked(),
            
            # Параметры сортировки
            'sort_by': self.current_sort_by,
            'ascending': self.current_ascending,
        }
        
        # Добавляем EXIF правила из виджета
        if hasattr(self, 'exif_widget'):
            rules.update(self.exif_widget.get_rules())
        
        return rules
        
    def preview_changes(self):
        # Предпросмотр изменений на основе правил
        if not self.current_files or not self.current_folder:
            QMessageBox.warning(self, "Внимание", "Сначала загрузите файлы!")
            return
        
        # Если уже есть запущенный воркер, останавливаем его
        if self.worker and self.worker.isRunning():
            print("Останавливаем предыдущий воркер перед запуском нового...")
            self.worker.stop()
            # Ждем немного для завершения
            import time
            time.sleep(0.5)
        
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
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()
        
    def on_worker_finished(self):
        """Обработчик завершения работы воркера"""
        print("Воркер завершил работу")
        self.worker = None  # Сбрасываем ссылку на воркер
    
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
        
        self.lowercase_ext.setChecked(True)
        self.remove_spaces.setChecked(False)
        self.keep_original.setChecked(False)
        self.filter_extensions.clear()
        self.min_size.setValue(0)
        self.sort_by_name.setChecked(True)
        self.sort_asc.setChecked(True)
        
        # Сбрасываем EXIF виджет
        if hasattr(self, 'exif_widget'):
            self.exif_widget.set_rules({
                'enable_exif': False,
                'exif_template': '{date}_{time}_{camera}_{focal}mm_F{aperture}_ISO{iso}',
                'clean_exif_names': True,
                'exif_lowercase': False,
                'exif_replace_spaces': True
            })
        
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
    
    def show_table_context_menu(self, position):
        """Показать контекстное меню для таблицы"""
        current_row = self.file_table.currentRow()
        if current_row < 0:
            return
        
        menu = QMenu()
    
        view_exif_action = menu.addAction("👁️ Просмотреть EXIF")
        preview_single_action = menu.addAction("🔍 Предпросмотр для этого файла")
    
        # Добавляем разделитель и новый пункт
        menu.addSeparator()
        help_action = menu.addAction("❓ Справка по переименованию")
    
        action = menu.exec_(self.file_table.mapToGlobal(position))
    
        if action == view_exif_action:
            self.show_exif_for_selected()
        elif action == preview_single_action:
            self.preview_single_file()
        elif action == help_action:
            self.show_context_help()

    def show_context_help(self):
        """Показать контекстную справку"""
        help_text = """
        💡 <b>Справка по переименованию:</b>
    
        <u>Доступные действия:</u>
        • 👁️ Просмотреть EXIF - детальная информация о фото
        • 🔍 Предпросмотр для файла - тест правил на одном файле
    
        <u>Экспресс-советы:</u>
        • Используйте EXIF для фото (вкладка EXIF)
        • Для документов - префиксы и нумерация
        • Регулярные выражения для сложных замен
    
        <u>Перейти к полной справке:</u>
        Откройте вкладку '❓ Помощь'
        """
    
        QMessageBox.information(self, "Контекстная справка", help_text)
    
    def on_file_double_clicked(self, item):
        """Обработка двойного клика по файлу"""
        if item.column() in [0, 1, 2]:  # Клик по имени файлу
            self.show_exif_for_selected()
    
    def preview_single_file(self):
        """Предпросмотр для выбранного файла"""
        current_row = self.file_table.currentRow()
        if current_row >= 0 and self.current_folder:
            filename = self.file_table.item(current_row, 1).text()
            file_path = os.path.join(self.current_folder, filename)
            
            if os.path.exists(file_path):
                # Собираем текущие правила
                rules = self.collect_rules()
                
                # Применяем правила только к этому файлу
                try:
                    new_name = RulesEngine.generate_new_name(filename, current_row, rules)
                    
                    # Применяем EXIF если нужно
                    if rules.get('enable_exif', False):
                        template = rules.get('exif_template', '{date}_{camera}')
                        exif_name = EXIFProcessor.generate_filename_from_exif(
                            new_name, file_path, template
                        )
                        
                        # Применяем дополнительные настройки
                        if rules.get('clean_exif_names', True):
                            exif_name = EXIFProcessor.clean_for_filename(exif_name)
                        
                        if rules.get('exif_lowercase', False):
                            name_part, ext = os.path.splitext(exif_name)
                            exif_name = name_part.lower() + ext
                        
                        if rules.get('exif_replace_spaces', True):
                            exif_name = exif_name.replace(' ', '_')
                        
                        new_name = exif_name
                    
                    # Показываем результат
                    QMessageBox.information(
                        self,
                        "Предпросмотр",
                        f"Файл: {filename}\n\n"
                        f"Будет переименован в:\n{new_name}\n\n"
                        f"Правила EXIF: {'Включены' if rules.get('enable_exif') else 'Выключены'}"
                    )
                    
                    # Обновляем ячейку в таблице
                    self.file_table.item(current_row, 2).setText(new_name)
                    
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка предпросмотра:\n{str(e)}")
            else:
                QMessageBox.warning(self, "Ошибка", "Файл не найден")
        else:
            QMessageBox.warning(self, "Внимание", "Сначала выберите файл в таблице")
    
    def show_exif_for_selected(self):
        """Показать EXIF данные для выбранного файла"""
        try:
            current_row = self.file_table.currentRow()
            if current_row >= 0 and self.current_folder:
                filename = self.file_table.item(current_row, 1).text()
                file_path = os.path.join(self.current_folder, filename)
                
                # Проверяем существование файла
                if not os.path.exists(file_path):
                    QMessageBox.warning(self, "Ошибка", f"Файл не найден:\n{file_path}")
                    return
                
                try:
                    # Проверяем, является ли файл изображением
                    image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', 
                                       '.bmp', '.gif', '.webp', '.heic', '.nef', 
                                       '.cr2', '.arw', '.dng']
                    ext = os.path.splitext(filename)[1].lower()
                    
                    if ext in image_extensions:
                        try:
                            # Создаем диалог с текущим окном как родителем
                            dialog = EXIFPreviewDialog(file_path, self)
                            
                            # Устанавливаем текущий шаблон из виджета
                            if hasattr(self, 'exif_widget'):
                                current_template = self.exif_widget.template_input.text()
                                dialog.template_input.setText(current_template)
                            
                            # Открываем как модальное окно
                            dialog.exec_()
                        except Exception as e:
                            QMessageBox.critical(self, "Ошибка", 
                                f"Не удалось открыть EXIF данные:\n{str(e)}\n\n"
                                f"Файл: {filename}\n"
                                f"Проверьте, что файл не поврежден и доступен для чтения.")
                    else:
                        QMessageBox.information(
                            self,
                            "Информация",
                            f"Файл {filename} не является изображением\n"
                            f"EXIF данные доступны только для изображений."
                        )
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", 
                        f"Ошибка при обработке файла:\n{str(e)}\n\n"
                        f"Файл: {filename}")
            else:
                QMessageBox.warning(self, "Внимание", "Сначала выберите файл в таблице")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", 
                f"Непредвиденная ошибка:\n{str(e)}\n\n"
                f"Попробуйте выбрать другой файл.")
    
    def setup_shortcuts(self):
        """Настройка горячих клавиш"""
        # F1 - открыть справку
        help_shortcut = QShortcut(QKeySequence.HelpContents, self)
        help_shortcut.activated.connect(self.open_help_tab)
    
        # Ctrl+H - тоже открыть справку
        ctrl_h_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        ctrl_h_shortcut.activated.connect(self.open_help_tab)

    def open_help_tab(self):
        """Открыть вкладку помощи"""
        # Переключаемся на вкладку помощи (6-я вкладка)
        self.tab_widget.setCurrentIndex(5)
        self.status_label.setText("Открыта справка пользователя")
        
    def on_exif_template_changed(self, template: str):
        """Обработка изменения EXIF шаблона"""
        if template and self.current_files:
            # Обновляем предпросмотр
            self.preview_changes()
