# Модуль для работы с EXIF данными изображений


import os
import re
from datetime import datetime
from typing import Dict, Optional, Any
from PIL import Image, ExifTags

class EXIFProcessor:
    # Класс для извлечения и обработки EXIF данных
    
    @staticmethod
    def get_exif_data(file_path: str) -> Optional[Dict]:
        """
        Извлечение EXIF данных из файла
        
        Args:
            file_path: Путь к файлу изображения
            
        Returns:
            Словарь с EXIF данными или None
        """
        try:
            with Image.open(file_path) as img:
                exif_data = img._getexif()
                
                if not exif_data:
                    return None
                
                # Преобразуем числовые теги в читаемые имена
                decoded_exif = {}
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    decoded_exif[tag] = value
                
                return decoded_exif
        except Exception as e:
            print(f"Ошибка при чтении EXIF данных из {file_path}: {e}")
            return None
    
    @staticmethod
    def get_creation_date(exif_data: Dict) -> Optional[datetime]:
        """
        Получение даты съемки из EXIF данных
        
        Args:
            exif_data: Словарь с EXIF данными
            
        Returns:
            Объект datetime с датой съемки или None
        """
        date_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
        
        for field in date_fields:
            if field in exif_data:
                try:
                    date_str = exif_data[field]
                    # Формат обычно: "YYYY:MM:DD HH:MM:SS"
                    date_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    return date_obj
                except (ValueError, TypeError):
                    continue
        
        return None
    
    @staticmethod
    def get_camera_model(exif_data: Dict) -> Optional[str]:
        # Получение модели камеры
        model = exif_data.get('Model')
        if model:
            return str(model).strip()
        return None
    
    @staticmethod
    def get_exposure_info(exif_data: Dict) -> Optional[str]:
        # Получение информации об экспозиции
        aperture = exif_data.get('FNumber')
        shutter_speed = exif_data.get('ExposureTime')
        iso = exif_data.get('ISOSpeedRatings')
        
        parts = []
        
        if aperture:
            try:
                # Aperture часто хранится как кортеж (числитель, знаменатель)
                if isinstance(aperture, tuple) and len(aperture) == 2:
                    aperture_value = aperture[0] / aperture[1]
                    parts.append(f"f/{aperture_value:.1f}")
                else:
                    parts.append(f"f/{float(aperture):.1f}")
            except (ValueError, TypeError):
                pass
        
        if shutter_speed:
            try:
                if isinstance(shutter_speed, tuple) and len(shutter_speed) == 2:
                    shutter_value = shutter_speed[0] / shutter_speed[1]
                    if shutter_value >= 1:
                        parts.append(f"{shutter_value:.0f}s")
                    else:
                        parts.append(f"1/{int(1/shutter_value)}s")
            except (ValueError, TypeError, ZeroDivisionError):
                pass
        
        if iso:
            parts.append(f"ISO{iso}")
        
        if parts:
            return "_".join(parts)
        return None
    
    @staticmethod
    def format_date_for_filename(date_obj: datetime, format_str: str) -> str:
        """
        Форматирование даты для использования в имени файла
        
        Args:
            date_obj: Объект datetime
            format_str: Строка формата
            
        Returns:
            Отформатированная дата
        """
        try:
            format_mapping = {
                'YYYY-MM-DD': '%Y-%m-%d',
                'DD-MM-YYYY': '%d-%m-%Y',
                'YYYYMMDD': '%Y%m%d',
                'MM-DD-YYYY': '%m-%d-%Y',
                'YY-MM-DD': '%y-%m-%d',
                'DD.MM.YYYY': '%d.%m.%Y'
            }
            
            py_format = format_mapping.get(format_str, '%Y-%m-%d')
            return date_obj.strftime(py_format)
        except Exception:
            return date_obj.strftime('%Y-%m-%d')
    
    @staticmethod
    def add_exif_to_filename(file_name: str, file_path: str, rules: Dict[str, Any]) -> str:
        """
        Добавление EXIF данных к имени файла
        
        Args:
            file_name: Текущее имя файла
            file_path: Полный путь к файлу
            rules: Правила с настройками EXIF
            
        Returns:
            Новое имя файла с EXIF данными
        """
        if not rules.get('enable_exif', False):
            return file_name
        
        # Проверяем, является ли файл изображением
        image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif']
        ext = os.path.splitext(file_name)[1].lower()
        
        if ext not in image_extensions:
            return file_name
        
        exif_data = EXIFProcessor.get_exif_data(file_path)
        if not exif_data:
            return file_name
        
        parts = []
        
        # Добавляем дату
        date_obj = EXIFProcessor.get_creation_date(exif_data)
        if date_obj:
            date_format = rules.get('date_format', 'YYYY-MM-DD')
            date_str = EXIFProcessor.format_date_for_filename(date_obj, date_format)
            parts.append(date_str)
        
        # Добавляем модель камеры
        if rules.get('use_camera_model', False):
            camera_model = EXIFProcessor.get_camera_model(exif_data)
            if camera_model:
                # Убираем пробелы и специальные символы
                camera_clean = re.sub(r'[^\w\-]', '_', camera_model)
                parts.append(camera_clean)
        
        # Добавляем параметры экспозиции
        if rules.get('use_exposure', False):
            exposure_info = EXIFProcessor.get_exposure_info(exif_data)
            if exposure_info:
                parts.append(exposure_info)
        
        if not parts:
            return file_name
        
        separator = rules.get('exif_separator', '_')
        exif_part = separator.join(parts)
        
        position = rules.get('exif_position', 'prefix')
        name, ext = os.path.splitext(file_name)
        
        if position == 'prefix':
            return f"{exif_part}{separator}{name}{ext}"
        else:  # suffix
            return f"{name}{separator}{exif_part}{ext}"