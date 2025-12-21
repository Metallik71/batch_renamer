# Модуль для работы с EXIF данными изображений

import os
import re
import json
from datetime import datetime
from typing import Dict, Optional, Any, List, Tuple
from PIL import Image, ExifTags
from PIL.ExifTags import GPSTAGS, TAGS


class EXIFProcessor:
    """Класс для работы со всеми EXIF-метаданными"""
    
    # Маппинг форматов даты
    DATE_FORMATS = {
        'YYYY-MM-DD': '%Y-%m-%d',
        'DD-MM-YYYY': '%d-%m-%Y',
        'YYYYMMDD': '%Y%m%d',
        'MM-DD-YYYY': '%m-%d-%Y',
        'YY-MM-DD': '%y-%m-%d',
        'DD.MM.YYYY': '%d.%m.%Y',
        'YYYY-MM-DD_HH-MM': '%Y-%m-%d_%H-%M',
        'YYYYMMDD_HHMMSS': '%Y%m%d_%H%M%S',
        'DDMMYYYY': '%d%m%Y'
    }
    
    # Поддерживаемые плейсхолдеры для шаблонов
    PLACEHOLDERS = {
        '{date}': 'Дата съемки (YYYY-MM-DD)',
        '{time}': 'Время съемки (HH-MM)',
        '{datetime}': 'Дата и время',
        '{camera}': 'Модель камеры',
        '{make}': 'Производитель камеры',
        '{lens}': 'Модель объектива',
        '{focal}': 'Фокусное расстояние (мм)',
        '{aperture}': 'Диафрагма (f/)',
        '{shutter}': 'Выдержка',
        '{iso}': 'ISO',
        '{width}': 'Ширина изображения',
        '{height}': 'Высота изображения',
        '{orientation}': 'Ориентация',
        '{artist}': 'Автор',
        '{copyright}': 'Копирайт',
        '{software}': 'Программное обеспечение',
        '{model}': 'Модель камеры (синоним {camera})'
    }
    
    @staticmethod
    def get_all_exif_data(file_path: str) -> Optional[Dict]:
        """
        Получение ВСЕХ EXIF данных из файла (БЕЗОПАСНАЯ ВЕРСИЯ)
        
        Args:
            file_path: Путь к файлу изображения
            
        Returns:
            Полный словарь с EXIF данными или пустой словарь в случае ошибки
        """
        try:
            # Проверка существования файла
            if not os.path.exists(file_path):
                return {}
            
            # Проверка, что это файл
            if not os.path.isfile(file_path):
                return {}
            
            # Проверка размера файла
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {}
            
            with Image.open(file_path) as img:
                exif_data = img.getexif()
                
                if not exif_data:
                    return {}
                
                decoded_exif = {}
                for tag_id, value in exif_data.items():
                    try:
                        tag_name = TAGS.get(tag_id, tag_id)
                        
                        # Обработка GPS данных
                        if tag_name == "GPSInfo" and isinstance(value, dict):
                            decoded_gps = {}
                            for gps_tag_id, gps_value in value.items():
                                try:
                                    gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                    decoded_gps[gps_tag_name] = gps_value
                                except:
                                    continue
                            decoded_exif[tag_name] = decoded_gps
                        else:
                            decoded_exif[tag_name] = value
                    except Exception:
                        continue  # Пропускаем проблемные теги
                
                return decoded_exif
        except Exception as e:
            print(f"Ошибка при чтении EXIF из {file_path}: {str(e)}")
            return {}
    
    @staticmethod
    def get_exif_value(exif_data: Dict, tag_name: str, default: Any = None) -> Any:
        """Безопасное получение значения EXIF тега"""
        if not exif_data:
            return default
        return exif_data.get(tag_name, default)
    
    @staticmethod
    def format_exif_value(tag: str, value: Any) -> str:
        """Форматирование значения EXIF тега для отображения (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        if value is None:
            return "N/A"
        
        try:
            # Специальные форматы для некоторых тегов
            if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                if isinstance(value, str):
                    try:
                        # Формат: "YYYY:MM:DD HH:MM:SS"
                        return value.replace(':', '-', 2)
                    except:
                        return str(value)
                return str(value)
            
            elif tag == 'FNumber':
                if isinstance(value, tuple) and len(value) == 2:
                    try:
                        return f"f/{value[0]/value[1]:.1f}"
                    except:
                        return str(value)
                elif isinstance(value, (int, float)):
                    return f"f/{value:.1f}"
            
            elif tag == 'ExposureTime':
                if isinstance(value, tuple) and len(value) == 2:
                    try:
                        exposure = value[0] / value[1]
                        if exposure < 1:
                            return f"1/{int(1/exposure)}"
                        return f"{exposure:.1f}"
                    except:
                        return str(value)
            
            elif tag == 'ISOSpeedRatings':
                return f"ISO {value}"
            
            elif tag == 'FocalLength':
                if isinstance(value, tuple) and len(value) == 2:
                    try:
                        return f"{int(value[0]/value[1])}mm"
                    except:
                        return str(value)
                elif isinstance(value, (int, float)):
                    return f"{int(value)}mm"
            
            elif tag == 'Flash':
                return EXIFProcessor._format_flash(value)
            
            elif tag == 'Orientation':
                try:
                    orientations = {
                        1: "Нормальная",
                        2: "Отзеркалена горизонтально",
                        3: "Повернута на 180°",
                        4: "Отзеркалена вертикально",
                        5: "Повернута на 90° + отзеркалена",
                        6: "Повернута на 90°",
                        7: "Повернута на -90° + отзеркалена",
                        8: "Повернута на -90°"
                    }
                    return orientations.get(int(value), f"Код: {value}")
                except:
                    return str(value)
            
            elif tag == 'ColorSpace':
                try:
                    colors = {1: 'sRGB', 2: 'Adobe RGB', 65535: 'Uncalibrated'}
                    return colors.get(int(value), str(value))
                except:
                    return str(value)
            
            elif tag == 'GPSInfo':
                if isinstance(value, dict):
                    coords = EXIFProcessor._extract_gps_coordinates(value)
                    if coords:
                        return f"{coords['latitude']:.6f}, {coords['longitude']:.6f}"
                    return "GPS данные присутствуют"
            
            return str(value)
        except Exception:
            return str(value)
    
    @staticmethod
    def _format_flash(flash_value: Any) -> str:
        """Форматирование информации о вспышке (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        if flash_value is None:
            return "Неизвестно"
        
        try:
            if isinstance(flash_value, int):
                flash_info = []
                if flash_value & 0x1:
                    flash_info.append("Сработала")
                if flash_value & 0x20:
                    flash_info.append("Подавление красных глаз")
                if flash_value & 0x40:
                    flash_info.append("Авто режим")
                
                return ", ".join(flash_info) if flash_info else "Не сработала"
            return str(flash_value)
        except Exception:
            return str(flash_value)
    
    @staticmethod
    def _extract_gps_coordinates(gps_info: Dict) -> Optional[Dict[str, float]]:
        """Извлечение GPS координат из словаря GPSInfo (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        try:
            if not isinstance(gps_info, dict):
                return None
                
            coords = {}
            
            # Широта
            if 2 in gps_info and 1 in gps_info:
                lat = gps_info[2]
                lat_ref = gps_info.get(1, 'N')
                lat_decimal = EXIFProcessor._convert_to_decimal(lat)
                if lat_ref in ['S', 's']:
                    lat_decimal = -lat_decimal
                coords['latitude'] = lat_decimal
            
            # Долгота
            if 4 in gps_info and 3 in gps_info:
                lon = gps_info[4]
                lon_ref = gps_info.get(3, 'E')
                lon_decimal = EXIFProcessor._convert_to_decimal(lon)
                if lon_ref in ['W', 'w']:
                    lon_decimal = -lon_decimal
                coords['longitude'] = lon_decimal
            
            return coords if coords else None
        except Exception:
            return None
    
    @staticmethod
    def _convert_to_decimal(coord_tuple) -> float:
        """Конвертация координат из градусов/минут/секунд в десятичные градусы (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        try:
            if isinstance(coord_tuple, tuple) and len(coord_tuple) == 3:
                degrees = 0.0
                minutes = 0.0
                seconds = 0.0
                
                # Обрабатываем градусы
                try:
                    if isinstance(coord_tuple[0], tuple):
                        degrees = coord_tuple[0][0] / coord_tuple[0][1]
                    else:
                        degrees = float(coord_tuple[0])
                except:
                    degrees = 0.0
                
                # Обрабатываем минуты
                try:
                    if isinstance(coord_tuple[1], tuple):
                        minutes = coord_tuple[1][0] / coord_tuple[1][1]
                    else:
                        minutes = float(coord_tuple[1])
                except:
                    minutes = 0.0
                
                # Обрабатываем секунды
                try:
                    if isinstance(coord_tuple[2], tuple):
                        seconds = coord_tuple[2][0] / coord_tuple[2][1]
                    else:
                        seconds = float(coord_tuple[2])
                except:
                    seconds = 0.0
                
                return degrees + minutes/60 + seconds/3600
            return 0.0
        except Exception:
            return 0.0
    
    @staticmethod
    def get_creation_datetime(exif_data: Dict) -> Optional[Tuple[datetime, str, str]]:
        """Получение даты и времени съемки (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        if not exif_data:
            return None
            
        date_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
        
        for field in date_fields:
            if field in exif_data:
                try:
                    date_str = exif_data[field]
                    if date_str is None:
                        continue
                        
                    if isinstance(date_str, bytes):
                        date_str = date_str.decode('utf-8', errors='ignore')
                    
                    # Формат: "YYYY:MM:DD HH:MM:SS"
                    date_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    date_part = date_obj.strftime("%Y-%m-%d")
                    time_part = date_obj.strftime("%H-%M")
                    
                    return date_obj, date_part, time_part
                except (ValueError, TypeError, AttributeError, KeyError):
                    continue
        
        return None
    
    @staticmethod
    def extract_values_for_template(exif_data: Dict) -> Dict[str, str]:
        """Извлечение всех значений для подстановки в шаблон (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        if not exif_data:
            return {}
            
        values = {}
        
        try:
            # Дата и время
            datetime_info = EXIFProcessor.get_creation_datetime(exif_data)
            if datetime_info:
                date_obj, date_part, time_part = datetime_info
                values['{date}'] = date_part
                values['{time}'] = time_part
                values['{datetime}'] = f"{date_part}_{time_part}"
            
            # Камера
            camera_model = exif_data.get('Model', '')
            if camera_model:
                values['{camera}'] = EXIFProcessor.clean_for_filename(str(camera_model))
                values['{model}'] = values['{camera}']  # Синоним
            
            # Производитель
            make = exif_data.get('Make', '')
            if make:
                values['{make}'] = EXIFProcessor.clean_for_filename(str(make))
            
            # Объектив
            lens = exif_data.get('LensModel', '')
            if lens:
                values['{lens}'] = EXIFProcessor.clean_for_filename(str(lens))
            
            # Фокусное расстояние
            focal = exif_data.get('FocalLength')
            if focal is not None:
                try:
                    if isinstance(focal, tuple) and len(focal) == 2:
                        values['{focal}'] = str(int(focal[0] / focal[1]))
                    else:
                        values['{focal}'] = str(int(float(focal)))
                except:
                    values['{focal}'] = ''
            else:
                values['{focal}'] = ''
            
            # Диафрагма
            aperture = exif_data.get('FNumber')
            if aperture is not None:
                try:
                    if isinstance(aperture, tuple) and len(aperture) == 2:
                        values['{aperture}'] = f"{aperture[0]/aperture[1]:.1f}"
                    else:
                        values['{aperture}'] = str(float(aperture))
                except:
                    values['{aperture}'] = ''
            else:
                values['{aperture}'] = ''
            
            # Выдержка
            shutter = exif_data.get('ExposureTime')
            if shutter is not None:
                try:
                    if isinstance(shutter, tuple) and len(shutter) == 2:
                        shutter_val = shutter[0] / shutter[1]
                        if shutter_val < 1:
                            values['{shutter}'] = f"{int(1/shutter_val)}"
                        else:
                            values['{shutter}'] = f"{shutter_val:.0f}"
                    else:
                        values['{shutter}'] = str(shutter)
                except:
                    values['{shutter}'] = ''
            else:
                values['{shutter}'] = ''
            
            # ISO
            iso = exif_data.get('ISOSpeedRatings')
            if iso is not None:
                values['{iso}'] = str(iso)
            else:
                values['{iso}'] = ''
            
            # Размеры изображения
            width = exif_data.get('ImageWidth')
            if width is not None:
                values['{width}'] = str(width)
            else:
                values['{width}'] = ''
            
            height = exif_data.get('ImageHeight')
            if height is not None:
                values['{height}'] = str(height)
            else:
                values['{height}'] = ''
            
            # Другое
            orientation = exif_data.get('Orientation')
            if orientation is not None:
                values['{orientation}'] = str(orientation)
            else:
                values['{orientation}'] = ''
            
            artist = exif_data.get('Artist')
            if artist:
                values['{artist}'] = EXIFProcessor.clean_for_filename(str(artist))
            else:
                values['{artist}'] = ''
            
            copyright = exif_data.get('Copyright')
            if copyright:
                values['{copyright}'] = EXIFProcessor.clean_for_filename(str(copyright))
            else:
                values['{copyright}'] = ''
            
            software = exif_data.get('Software')
            if software:
                values['{software}'] = EXIFProcessor.clean_for_filename(str(software))
            else:
                values['{software}'] = ''
            
        except Exception as e:
            print(f"Ошибка при извлечении значений EXIF: {e}")
            # Возвращаем пустые значения в случае ошибки
            return {key: '' for key in EXIFProcessor.PLACEHOLDERS.keys()}
        
        return values
    
    @staticmethod
    def generate_filename_from_exif(file_name: str, file_path: str, template: str) -> str:
        """
        Генерация имени файла по шаблону с EXIF данными (БЕЗОПАСНАЯ ВЕРСИЯ)
        
        Args:
            file_name: Текущее имя файла
            file_path: Полный путь к файлу
            template: Шаблон с плейсхолдерами
            
        Returns:
            Новое имя файла или оригинальное имя в случае ошибки
        """
        try:
            # Получаем EXIF данные
            exif_data = EXIFProcessor.get_all_exif_data(file_path)
            if not exif_data:
                return file_name
            
            # Извлекаем значения для подстановки
            values = EXIFProcessor.extract_values_for_template(exif_data)
            
            # Применяем шаблон
            result = template
            for placeholder, value in values.items():
                if value:  # Заменяем только если есть значение
                    result = result.replace(placeholder, value)
            
            # Если после замены остались плейсхолдеры - удаляем их
            for placeholder in EXIFProcessor.PLACEHOLDERS.keys():
                result = result.replace(placeholder, '')
            
            # Очищаем от пустых сегментов (например, двойные подчеркивания)
            result = re.sub(r'_+', '_', result)
            result = re.sub(r'^_|_$', '', result)  # Удаляем подчеркивания в начале/конце
            
            # Если результат пустой или содержит только разделители, возвращаем исходное имя
            if not result or result.replace('_', '').replace('-', '') == '':
                return file_name
            
            # Добавляем расширение
            name, ext = os.path.splitext(file_name)
            return result + ext
            
        except Exception as e:
            print(f"Ошибка при генерации имени из EXIF: {e}")
            return file_name
    
    @staticmethod
    def clean_for_filename(text: Any) -> str:
        """
        Очистка текста для использования в имени файла (БЕЗОПАСНАЯ ВЕРСИЯ)
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст
        """
        if text is None:
            return ""
        
        try:
            text_str = str(text)
            
            # Удаляем недопустимые символы
            cleaned = re.sub(r'[<>:"/\\|?*]', '', text_str)
            
            # Заменяем несколько пробелов на один
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            # Обрезаем пробелы по краям
            cleaned = cleaned.strip()
            
            return cleaned
        except Exception:
            return ""
    
    @staticmethod
    def get_supported_placeholders() -> Dict[str, str]:
        """Получить список поддерживаемых плейсхолдеров"""
        return EXIFProcessor.PLACEHOLDERS.copy()
    
    @staticmethod
    def validate_template(template: str) -> Tuple[bool, str]:
        """Валидация шаблона (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        if not template:
            return False, "Шаблон не может быть пустым"
        
        try:
            # Проверяем наличие хотя бы одного валидного плейсхолдера
            has_valid_placeholder = False
            for placeholder in EXIFProcessor.PLACEHOLDERS.keys():
                if placeholder in template:
                    has_valid_placeholder = True
                    break
            
            if not has_valid_placeholder and '{' in template:
                # Проверяем наличие незакрытых фигурных скобок
                if template.count('{') != template.count('}'):
                    return False, "Непарные фигурные скобки в шаблоне"
                return False, "Неизвестный плейсхолдер в шаблоне"
            
            return True, "OK"
        except Exception as e:
            return False, f"Ошибка валидации шаблона: {str(e)}"
    
    @staticmethod
    def get_available_placeholders(exif_data: Dict) -> List[str]:
        """Получить список доступных плейсхолдеров для данных EXIF"""
        available = []
        values = EXIFProcessor.extract_values_for_template(exif_data)
        
        for placeholder, value in values.items():
            if value:  # Плейсхолдер доступен если есть значение
                available.append(placeholder)
        
        return available
    
    @staticmethod
    def preview_template(template: str, exif_data: Dict) -> str:
        """Предпросмотр шаблона с данными EXIF (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        if not exif_data:
            return "Нет EXIF данных"
        
        try:
            values = EXIFProcessor.extract_values_for_template(exif_data)
            result = template
            
            for placeholder, value in values.items():
                if value:
                    result = result.replace(placeholder, f"[{value}]")
            
            # Показываем необработанные плейсхолдеры
            for placeholder in EXIFProcessor.PLACEHOLDERS.keys():
                if placeholder in result:
                    result = result.replace(placeholder, f"<{placeholder}>")
            
            return result
        except Exception:
            return "Ошибка при предпросмотре шаблона"
    
    @staticmethod
    def export_exif_to_json(file_path: str, output_path: str = None) -> str:
        """Экспорт EXIF данных в JSON файл (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        try:
            exif_data = EXIFProcessor.get_all_exif_data(file_path)
            if not exif_data:
                return ""
            
            if output_path is None:
                base_name = os.path.splitext(file_path)[0]
                output_path = f"{base_name}_exif.json"
            
            # Конвертируем в JSON-совместимый формат
            def json_serializer(obj):
                if isinstance(obj, bytes):
                    try:
                        return obj.decode('utf-8', errors='ignore')
                    except:
                        return str(obj)
                raise TypeError(f"Type {type(obj)} not serializable")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(exif_data, f, indent=2, default=json_serializer)
            
            return output_path
        except Exception as e:
            print(f"Ошибка при экспорте EXIF: {e}")
            return ""
    
    @staticmethod
    def get_exif_summary(file_path: str) -> Dict[str, Any]:
        """Получить сводку EXIF данных (БЕЗОПАСНАЯ ВЕРСИЯ)"""
        try:
            exif_data = EXIFProcessor.get_all_exif_data(file_path)
            if not exif_data:
                return {'has_exif': False}
            
            summary = {
                'has_exif': True,
                'camera': '',
                'make': '',
                'date': '',
                'time': '',
                'lens': '',
                'focal_length': '',
                'aperture': '',
                'shutter_speed': '',
                'iso': '',
                'dimensions': '',
                'has_gps': False
            }
            
            # Камера
            camera_model = exif_data.get('Model', '')
            if camera_model:
                summary['camera'] = str(camera_model)
            
            # Производитель
            make = exif_data.get('Make', '')
            if make:
                summary['make'] = str(make)
            
            # Объектив
            lens = exif_data.get('LensModel', '')
            if lens:
                summary['lens'] = str(lens)
            
            # Дата и время
            datetime_info = EXIFProcessor.get_creation_datetime(exif_data)
            if datetime_info:
                _, date_part, time_part = datetime_info
                summary['date'] = date_part
                summary['time'] = time_part
            
            # Фокусное расстояние
            focal = exif_data.get('FocalLength')
            if focal is not None:
                try:
                    if isinstance(focal, tuple) and len(focal) == 2:
                        summary['focal_length'] = f"{int(focal[0]/focal[1])}mm"
                except:
                    pass
            
            # Диафрагма
            aperture = exif_data.get('FNumber')
            if aperture is not None:
                try:
                    if isinstance(aperture, tuple) and len(aperture) == 2:
                        summary['aperture'] = f"f/{aperture[0]/aperture[1]:.1f}"
                except:
                    pass
            
            # Выдержка
            shutter = exif_data.get('ExposureTime')
            if shutter is not None:
                try:
                    if isinstance(shutter, tuple) and len(shutter) == 2:
                        shutter_val = shutter[0] / shutter[1]
                        if shutter_val < 1:
                            summary['shutter_speed'] = f"1/{int(1/shutter_val)}"
                        else:
                            summary['shutter_speed'] = f"{shutter_val:.0f}"
                except:
                    pass
            
            # ISO
            iso = exif_data.get('ISOSpeedRatings')
            if iso is not None:
                summary['iso'] = f"ISO {iso}"
            
            # Размеры
            width = exif_data.get('ImageWidth')
            height = exif_data.get('ImageHeight')
            if width and height:
                summary['dimensions'] = f"{width}x{height}"
            
            # GPS
            summary['has_gps'] = 'GPSInfo' in exif_data
            
            return summary
            
        except Exception as e:
            print(f"Ошибка при получении сводки EXIF: {e}")
            return {'has_exif': False, 'error': str(e)}
