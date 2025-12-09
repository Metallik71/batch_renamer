# Движок для обработки правил переименования


import os
import re
from typing import Dict, Any, List, Optional

class RulesEngine:
    # Движок для применения правил переименования
    
    @staticmethod
    def apply_text_replace(file_name: str, rules: Dict[str, Any]) -> str:
        # Применение простой замены текста
        if not rules.get('enable_replace', False):
            return file_name
        
        replace_from = rules.get('replace_from', '')
        replace_to = rules.get('replace_to', '')
        
        if not replace_from:
            return file_name
        
        case_sensitive = rules.get('case_sensitive', False)
        replace_all = rules.get('replace_all', True)
        
        if case_sensitive:
            if replace_all:
                return file_name.replace(replace_from, replace_to)
            else:
                return file_name.replace(replace_from, replace_to, 1)
        else:
            # Нечувствительная к регистру замена
            pattern = re.compile(re.escape(replace_from), re.IGNORECASE)
            if replace_all:
                return pattern.sub(replace_to, file_name)
            else:
                return pattern.sub(replace_to, file_name, count=1)
    
    @staticmethod
    def apply_prefix_suffix(file_name: str, rules: Dict[str, Any]) -> str:
        # Применение префикса и суффикса
        if not rules.get('enable_prefix_suffix', False):
            return file_name
        
        result = file_name
        prefix = rules.get('prefix', '')
        suffix = rules.get('suffix', '')
        
        if prefix:
            result = prefix + result
        
        if suffix:
            suffix_before_ext = rules.get('suffix_before_ext', True)
            if suffix_before_ext:
                name, ext = os.path.splitext(result)
                result = name + suffix + ext
            else:
                result = result + suffix
        
        return result
    
    @staticmethod
    def apply_numbering(file_name: str, index: int, rules: Dict[str, Any]) -> str:
        # Применение нумерации
        if not rules.get('enable_numbering', False):
            return file_name
        
        start_number = rules.get('start_number', 1)
        digits_count = rules.get('digits_count', 3)
        separator = rules.get('number_separator', '_')
        number_position = rules.get('number_position', 'suffix')
        
        number = str(start_number + index).zfill(digits_count)
        
        if number_position == 'prefix':
            return f"{number}{separator}{file_name}"
        else:  # suffix
            name, ext = os.path.splitext(file_name)
            return f"{name}{separator}{number}{ext}"
    
    @staticmethod
    def apply_regex(file_name: str, rules: Dict[str, Any]) -> str:
        # Применение регулярных выражений
        if not rules.get('enable_regex', False):
            return file_name
        
        pattern = rules.get('regex_pattern', '')
        replacement = rules.get('regex_replacement', '')
        
        if not pattern:
            return file_name
        
        try:
            flags = re.IGNORECASE if rules.get('regex_ignore_case', False) else 0
            if rules.get('regex_dotall', False):
                flags |= re.DOTALL
            
            return re.sub(pattern, replacement, file_name, flags=flags)
        except Exception:
            # В случае ошибки в регулярном выражении возвращаем оригинальное имя
            return file_name
    
    @staticmethod
    def apply_extension_processing(file_name: str, rules: Dict[str, Any]) -> str:
        # Обработка расширений файлов и удаление пробелов
        result = file_name
        
        # Удаление пробелов
        if rules.get('remove_spaces', False):
            result = result.replace(' ', '')
        
        # Приведение расширения к нижнему регистру
        if rules.get('lowercase_ext', True):
            name, ext = os.path.splitext(result)
            result = name + ext.lower()
        
        return result
    
    @staticmethod
    def generate_new_name(file_name: str, index: int, rules: Dict[str, Any]) -> str:
        """
        Генерация нового имени файла на основе всех правил
        
        Args:
            file_name: Исходное имя файла
            index: Индекс файла в списке (для нумерации)
            rules: Словарь с правилами
            
        Returns:
            Новое имя файла
        """
        # Применяем правила в определенном порядке
        result = file_name
        
        # 1. Удаление пробелов (самое первое)
        if rules.get('remove_spaces', False):
            result = result.replace(' ', '')
        
        # 2. Замена текста
        result = RulesEngine.apply_text_replace(result, rules)
        
        # 3. Регулярные выражения
        result = RulesEngine.apply_regex(result, rules)
        
        # 4. Префикс/суффикс (до нумерации)
        result = RulesEngine.apply_prefix_suffix(result, rules)
        
        # 5. Нумерация
        result = RulesEngine.apply_numbering(result, index, rules)
        
        # 6. Приведение расширения к нижнему регистру (самое последнее)
        if rules.get('lowercase_ext', True):
            name, ext = os.path.splitext(result)
            result = name + ext.lower()
        
        return result
    
    @staticmethod
    def debug_generate_new_name(file_name: str, index: int, rules: Dict[str, Any]) -> str:
        """
        Отладочная версия для отслеживания шагов
        """
        print(f"\n--- Обработка файла: {file_name}, индекс: {index} ---")
        
        result = file_name
        print(f"Исходное имя: {result}")
        
        # Удаление пробелов
        if rules.get('remove_spaces', False):
            result = result.replace(' ', '')
            print(f"После удаления пробелов: {result}")
        
        # Замена текста
        if rules.get('enable_replace', False):
            old_result = result
            result = RulesEngine.apply_text_replace(result, rules)
            if result != old_result:
                print(f"После замены текста: {result}")
        
        # Регулярные выражения
        if rules.get('enable_regex', False):
            old_result = result
            result = RulesEngine.apply_regex(result, rules)
            if result != old_result:
                print(f"После регулярных выражений: {result}")
        
        # Префикс/суффикс
        if rules.get('enable_prefix_suffix', False):
            old_result = result
            result = RulesEngine.apply_prefix_suffix(result, rules)
            if result != old_result:
                print(f"После префикса/суффикса: {result}")
        
        # Нумерация
        if rules.get('enable_numbering', False):
            old_result = result
            result = RulesEngine.apply_numbering(result, index, rules)
            print(f"После нумерации: {result}")
        
        # Приведение расширений
        if rules.get('lowercase_ext', True):
            name, ext = os.path.splitext(result)
            result = name + ext.lower()
            print(f"После приведения расширений: {result}")
        
        print(f"Итоговое имя: {result}")
        return result
    
    @staticmethod
    def batch_process(files: List[str], rules: Dict[str, Any]) -> Dict[str, str]:
        """
        Пакетная обработка списка файлов
        
        Args:
            files: Список исходных имен файлов
            rules: Словарь с правилами
            
        Returns:
            Словарь {старое_имя: новое_имя}
        """
        result = {}
        
        for i, file_name in enumerate(files):
            new_name = RulesEngine.generate_new_name(file_name, i, rules)
            result[file_name] = new_name
        
        return result
    
    @staticmethod
    def validate_rules(rules: Dict[str, Any]) -> tuple[bool, str]:
        """
        Валидация правил
        
        Args:
            rules: Словарь с правилами
            
        Returns:
            Кортеж (валидно, сообщение_об_ошибке)
        """
        try:
            # Проверка регулярного выражения
            if rules.get('enable_regex', False):
                pattern = rules.get('regex_pattern', '')
                if pattern:
                    # Попытка компиляции регулярного выражения
                    flags = re.IGNORECASE if rules.get('regex_ignore_case', False) else 0
                    if rules.get('regex_dotall', False):
                        flags |= re.DOTALL
                    re.compile(pattern, flags)
            
            # Проверка замены текста
            if rules.get('enable_replace', False):
                replace_from = rules.get('replace_from', '')
                if not replace_from:
                    return True, ""  # Пустая замена - это ок
            
            return True, ""
            
        except re.error as e:
            return False, f"Ошибка в регулярном выражении: {str(e)}"
        except Exception as e:
            return False, f"Ошибка в правилах: {str(e)}"
