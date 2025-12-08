# Модуль для управления откатом операций


import os
import shutil
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

@dataclass
class RenameOperation:
    # Информация об операции переименования
    timestamp: datetime
    folder_path: str
    changes: List[Dict[str, str]]  # Список словарей {'old': 'new'}
    operation_id: str
    
    def to_dict(self) -> Dict:
        # Конвертация в словарь для сохранения
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RenameOperation':
        # Создание из словаря
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class UndoManager:
    # Менеджер для отката операций переименования
    
    def __init__(self, max_operations: int = 10):
        self.max_operations = max_operations
        self.operations: List[RenameOperation] = []
        self.backup_folder = ".renamer_backups"
        
    def create_operation_id(self) -> str:
        # Создание уникального ID для операции
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    def add_operation(self, folder_path: str, changes: List[Dict[str, str]]) -> str:
        """
        Добавление новой операции в историю
        
        Args:
            folder_path: Путь к папке с файлами
            changes: Список изменений [{'old': 'file1.txt', 'new': 'file1_new.txt'}, ...]
            
        Returns:
            ID операции
        """
        # Ограничиваем количество хранимых операций
        if len(self.operations) >= self.max_operations:
            self.operations.pop(0)
        
        operation_id = self.create_operation_id()
        operation = RenameOperation(
            timestamp=datetime.now(),
            folder_path=folder_path,
            changes=changes,
            operation_id=operation_id
        )
        
        self.operations.append(operation)
        return operation_id
    
    def get_last_operation(self) -> Optional[RenameOperation]:
        # Получение последней операции
        if self.operations:
            return self.operations[-1]
        return None
    
    def undo_last_operation(self) -> bool:
        """
        Откат последней операции
        
        Returns:
            True если успешно, False если нет операций для отката
        """
        if not self.operations:
            return False
        
        operation = self.operations.pop()
        
        try:
            success_count = 0
            error_count = 0
            
            for change in operation.changes:
                old_name = change['old']
                new_name = change['new']
                
                old_path = os.path.join(operation.folder_path, new_name)
                new_path = os.path.join(operation.folder_path, old_name)
                
                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
                    success_count += 1
                else:
                    error_count += 1
                    print(f"Файл не найден для отката: {old_path}")
            
            print(f"Откат выполнен: {success_count} успешно, {error_count} с ошибками")
            return success_count > 0
            
        except Exception as e:
            print(f"Ошибка при откате операции: {e}")
            # Возвращаем операцию обратно в стек при ошибке
            self.operations.append(operation)
            return False
    
    def create_backup(self, folder_path: str, files: List[str]) -> Optional[str]:
        """
        Создание резервной копии файлов
        
        Args:
            folder_path: Путь к папке с файлами
            files: Список файлов для резервного копирования
            
        Returns:
            Путь к папке с резервными копиями или None в случае ошибки
        """
        try:
            # Создаем папку для резервных копий
            if not os.path.exists(self.backup_folder):
                os.makedirs(self.backup_folder)
            
            # Создаем подпапку для этой операции
            backup_id = self.create_operation_id()
            backup_path = os.path.join(self.backup_folder, backup_id)
            os.makedirs(backup_path)
            
            # Копируем файлы
            for file_name in files:
                src = os.path.join(folder_path, file_name)
                dst = os.path.join(backup_path, file_name)
                shutil.copy2(src, dst)
            
            return backup_path
            
        except Exception as e:
            print(f"Ошибка при создании резервной копии: {e}")
            return None
    
    def restore_from_backup(self, backup_path: str, target_folder: str) -> bool:
        """
        Восстановление файлов из резервной копии
        
        Args:
            backup_path: Путь к папке с резервными копиями
            target_folder: Папка для восстановления
            
        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            if not os.path.exists(backup_path):
                return False
            
            success_count = 0
            error_count = 0
            
            for file_name in os.listdir(backup_path):
                src = os.path.join(backup_path, file_name)
                dst = os.path.join(target_folder, file_name)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    success_count += 1
            
            print(f"Восстановление из резервной копии: {success_count} файлов")
            return success_count > 0
            
        except Exception as e:
            print(f"Ошибка при восстановлении из резервной копии: {e}")
            return False
    
    def save_history(self, file_path: str) -> bool:
        # Сохранение истории операций в файл
        try:
            data = [op.to_dict() for op in self.operations]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка при сохранении истории: {e}")
            return False
    
    def load_history(self, file_path: str) -> bool:
        # Загрузка истории операций из файл
        try:
            if not os.path.exists(file_path):
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.operations = [RenameOperation.from_dict(op) for op in data]
            return True
        except Exception as e:
            print(f"Ошибка при загрузке истории: {e}")
            return False
    
    def clear_history(self):
        # Очистка истории операций
        self.operations.clear()
        
        # Удаляем папку с резервными копиями
        if os.path.exists(self.backup_folder):
            try:
                shutil.rmtree(self.backup_folder)
            except Exception as e:
                print(f"Ошибка при удалении резервных копий: {e}")