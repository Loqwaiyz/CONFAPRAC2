import argparse
import sys
from typing import Dict, List, Optional

# --- 1. Модель данных репозитория Alpine Linux (Имитация APKINDEX) ---
# Каждая запись имитирует ключевые поля из метаданных пакета, 
# где 'depends' соответствует полю D: (Dependencies) в APKINDEX.
# Зависимости перечислены в формате 'имя_пакета' или 'имя_пакета>=версия'.
# Мы будем брать только 'имя_пакета', игнорируя условия версий (>=, <, ~).

MOCK_REPOSITORY: Dict[str, List[str]] = {
    # Пакет 'busybox' имеет 3 прямые зависимости (virtual, musl, libcrypto).
    "busybox": ["musl", "alpine-baselayout", "libcrypto1.1"],
    
    # Пакет 'python3' зависит от busybox, openssl, и libc.
    "python3": ["busybox", "libssl1.1", "zlib", "libffi"],
    
    # Пакет 'openssl' зависит от libc и libcrypto.
    "openssl": ["libcrypto1.1", "musl"],
    
    # 'musl' и 'alpine-baselayout' - базовые пакеты без других зависимостей.
    "musl": [],
    "libcrypto1.1": [],
    "zlib": [],
    "libffi": [],
    "alpine-baselayout": [],
    
    # Несуществующий пакет для проверки ошибки
    "non-existent-pkg": [] 
}

# -----------------------------------------------------------------------

def extract_dependencies(package_name: str, repository: Dict[str, List[str]]) -> Optional[List[str]]:
    """
    Имитирует извлечение прямых зависимостей для заданного пакета 
    из смоделированного репозитория.

    Args:
        package_name: Имя пакета для анализа.
        repository: Смоделированная структура данных репозитория.

    Returns:
        Список прямых зависимостей или None, если пакет не найден.
    """
    
    # Нормализуем имя, чтобы оно соответствовало ключам (без условий версий)
    # В реальном APKTOOLS, зависимости могут быть в формате 'pkgname>=version'.
    # Здесь мы упрощаем:
    normalized_name = package_name.split('>=')[0].split('<')[0].split('~')[0]
    
    # 2. Извлечь информацию о прямых зависимостях заданного пользователем пакета.
    # Реальная логика: загрузить и распарсить APKINDEX с repository_url.
    # Прототип: ищем в MOCK_REPOSITORY.
    
    dependencies_with_versions = repository.get(normalized_name)
    
    if dependencies_with_versions is None:
        return None # Пакет не найден в репозитории
    
    # В APKINDEX зависимости могут содержать условия версий (e.g., 'musl>=1.2.3')
    # Для построения графа нам нужно только имя.
    direct_dependencies = []
    for dep in dependencies_with_versions:
        # Убираем все условия версий ('zlib', а не 'zlib>=1.2.3')
        # Для простоты прототипа просто берем первую часть до первого не-алфавитного символа, 
        # или до конца строки, если условия нет.
        name = dep.split('<')[0].split('>')[0].split('=')[0].split('~')[0].strip()
        direct_dependencies.append(name)
        
    return direct_dependencies


def run_visualizer(package_name: str, repository_url: str, repository_mode: str, output_filename: str, filter_substring: str):
    """
    Основная логика приложения.
    """
    
    print("--- Конфигурация инструмента визуализации графа зависимостей ---")
    print(f"Имя анализируемого пакета: **{package_name}**")
    print(f"URL/Путь репозитория: **{repository_url}**")
    print(f"Режим работы с репозиторием: **{repository_mode}**")
    print(f"Имя выходного файла графа: **{output_filename}**")
    print(f"Подстрока для фильтрации пакетов: **{filter_substring}**")
    print("------------------------------------------------------------------\n")
    
    # --- Сбор данных (Этап 2) ---
    
    print(f"Запрос зависимостей для пакета: **{package_name}**...")
    
    # 
    # В реальном приложении здесь будет логика загрузки 
    # APKINDEX.tar.gz с repository_url, распаковка и парсинг.
    # Для прототипа используем MOCK_REPOSITORY.
    #
    
    dependencies = extract_dependencies(package_name, MOCK_REPOSITORY)
    
    if dependencies is None:
        print(f"Ошибка: Пакет '{package_name}' не найден в смоделированном репозитории.")
        return
    
    # 3. (только для этого этапа) Вывести на экран все прямые зависимости.
    print(f"Прямые зависимости '{package_name}' найдены:")
    if dependencies:
        for dep in dependencies:
            print(f"- **{dep}**")
    else:
        print("- **Нет прямых зависимостей** (базовый пакет).")


def main():
    parser = argparse.ArgumentParser(
        description="Инструмент визуализации графа зависимостей для пакетного менеджера (Прототип, Этап 2).",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '-p', '--package', 
        type=str, 
        required=True, 
        dest='package_name',
        help='Имя анализируемого пакета (обязательный параметр).'
    )

    parser.add_argument(
        '-r', '--repo', 
        type=str, 
        default='https://dl-cdn.alpinelinux.org/alpine/v3.18/main', 
        dest='repository_url',
        help='URL-адрес репозитория (по умолчанию: Alpine v3.18/main).'
    )

    parser.add_argument(
        '-m', '--mode', 
        choices=['remote', 'local'], 
        default='remote', 
        dest='repository_mode',
        help='Режим работы с тестовым репозиторием (remote/local, по умолчанию: remote).'
    )

    parser.add_argument(
        '-o', '--output', 
        type=str, 
        default='dependency_graph.png', 
        dest='output_filename',
        help='Имя сгенерированного файла с изображением графа.'
    )

    parser.add_argument(
        '-f', '--filter', 
        type=str, 
        default='', 
        dest='filter_substring',
        help='Подстрока для фильтрации пакетов.'
    )

    args = parser.parse_args()

    # В целях демонстрации этапа, мы передаем только имя пакета 
    # для получения зависимостей из заглушки MOCK_REPOSITORY
    run_visualizer(
        args.package_name,
        args.repository_url,
        args.repository_mode,
        args.output_filename,
        args.filter_substring
    )

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nКритическая ошибка приложения: {e}", file=sys.stderr)
        sys.exit(1)