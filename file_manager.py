# Модуль для работы с файлами: загрузка, фильтрация, сортировка


import os
import fnmatch
from typing import List, Dict, Tuple, Optional, Callable
from datetime import datetime

class FileManager:
    # Менеджер для работы с файлами
    
    @staticmethod
    def get_files_from_folder(folder_path: str) -> List[str]:
        """
        Получить список файлов из папки
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Список имен файлов
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Папка не существует: {folder_path}")
        
        files = []
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                files.append(item)
        
        return files
    
    @staticmethod
    def filter_files_by_extension(files: List[str], extensions: str) -> List[str]:
        """
        Фильтрация файлов по расширениям
        
        Args:
            files: Список имен файлов
            extensions: Строка с расширениями через запятую (например: "jpg,png,pdf")
            
        Returns:
            Отфильтрованный список файлов
        """
        if not extensions or extensions.strip() == "":
            return files
        
        extensions_list = [ext.strip().lower() for ext in extensions.split(',')]
        extensions_list = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions_list]
        
        filtered = []
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in extensions_list:
                filtered.append(file)
        
        return filtered
    
    @staticmethod
    def filter_files_by_size(files: List[str], folder_path: str, min_size_kb: int = 0) -> List[str]:
        """
        Фильтрация файлов по минимальному размеру
        
        Args:
            files: Список имен файлов
            folder_path: Путь к папке с файлами
            min_size_kb: Минимальный размер в килобайтах
            
        Returns:
            Отфильтрованный список файлов
        """
        if min_size_kb <= 0:
            return files
        
        min_size_bytes = min_size_kb * 1024
        filtered = []
        
        for file in files:
            file_path = os.path.join(folder_path, file)
            try:
                if os.path.getsize(file_path) >= min_size_bytes:
                    filtered.append(file)
            except (OSError, IOError):
                continue
        
        return filtered
    
    @staticmethod
    def sort_files(files: List[str], folder_path: str, 
                   sort_by: str = 'name', ascending: bool = True) -> List[str]:
        """
        Сортировка файлов
        
        Args:
            files: Список имен файлов
            folder_path: Путь к папке с файлами
            sort_by: Критерий сортировки ('name', 'date', 'size')
            ascending: По возрастанию
            
        Returns:
            Отсортированный список файлов
        """
        if not files:
            return files
        
        file_info = []
        
        for file in files:
            file_path = os.path.join(folder_path, file)
            try:
                stat = os.stat(file_path)
                info = {
                    'name': file,
                    'size': stat.st_size,
                    'created': stat.st_ctime,
                    'modified': stat.st_mtime
                }
                file_info.append(info)
            except (OSError, IOError):
                continue
        
        if sort_by == 'name':
            file_info.sort(key=lambda x: x['name'].lower(), reverse=not ascending)
        elif sort_by == 'size':
            file_info.sort(key=lambda x: x['size'], reverse=not ascending)
        elif sort_by == 'date':
            file_info.sort(key=lambda x: x['created'], reverse=not ascending)
        
        return [info['name'] for info in file_info]
    
    @staticmethod
    def rename_file(old_path: str, new_name: str, keep_original: bool = False) -> bool:
        """
        Переименование файла
        
        Args:
            old_path: Полный путь к исходному файлу
            new_name: Новое имя файла
            keep_original: Сохранять копию оригинального файла
            
        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            folder = os.path.dirname(old_path)
            new_path = os.path.join(folder, new_name)
            
            # Проверяем, не существует ли уже файл с таким именем
            if os.path.exists(new_path) and new_path != old_path:
                return False
            
            # Если нужно сохранить оригинал, создаем копию
            if keep_original:
                import shutil
                backup_path = old_path + '.backup'
                shutil.copy2(old_path, backup_path)
            
            # Переименовываем файл
            os.rename(old_path, new_path)
            return True
            
        except Exception as e:
            print(f"Ошибка при переименовании {old_path}: {e}")
            return False
    
    @staticmethod
    def validate_file_name(file_name: str) -> Tuple[bool, str]:
        """
        Проверка имени файла на валидность
        
        Args:
            file_name: Имя файла для проверки
            
        Returns:
            Кортеж (валидно ли имя, сообщение об ошибке)
        """
        if not file_name or file_name.strip() == "":
            return False, "Имя файла не может быть пустым"
        
        # Запрещенные символы в именах файлов
        forbidden_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in forbidden_chars:
            if char in file_name:
                return False, f"Имя файла содержит запрещенный символ: {char}"
        
        # Проверка длины
        if len(file_name) > 255:
            return False, "Имя файла слишком длинное (максимум 255 символов)"
        
        # Проверка на зарезервированные имена Windows
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 
                         'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                         'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        
        name_without_ext = os.path.splitext(file_name)[0].upper()
        if name_without_ext in reserved_names:
            return False, f"Имя файла зарезервировано системой: {name_without_ext}"
        
        return True, "OK"