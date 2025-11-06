import argparse
import sys
from typing import Dict, List, Set, Tuple

# --- Модель данных репозитория Alpine Linux (Имитация APKINDEX для remote) ---
# Ключи: имя пакета, Значения: список прямых зависимостей.
MOCK_REPOSITORY: Dict[str, List[str]] = {
    "busybox": ["musl", "alpine-baselayout", "libcrypto1.1"],
    "python3": ["busybox", "libssl1.1", "zlib", "libffi"],
    "openssl": ["libcrypto1.1", "musl"],
    "musl": [],
    "libcrypto1.1": [],
    "zlib": [],
    "libffi": [],
    "alpine-baselayout": [],
}
# -----------------------------------------------------------------------------

def load_local_repository(file_path: str) -> Dict[str, List[str]]:
    """
    4. Поддержка тестового режима: Загружает граф зависимостей из простого 
    локального текстового файла.
    Формат файла: PACKAGE: DEP1, DEP2, ... (где PACKAGE - заглавные буквы)
    """
    repo = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if ':' in line:
                    package, deps_str = line.split(':', 1)
                    package = package.strip()
                    # Разбиваем строку зависимостей, игнорируя пустые элементы
                    deps = [d.strip() for d in deps_str.split(',') if d.strip()]
                    repo[package] = deps
    except FileNotFoundError:
        print(f"Ошибка: Файл тестового репозитория не найден по пути: {file_path}")
        return {} 
    except Exception as e:
        print(f"Ошибка при чтении файла тестового репозитория: {e}")
        return {}
    
    return repo

def build_dependency_graph_bfs(
    start_package: str, 
    repository_data: Dict[str, List[str]], 
    filter_substring: str
) -> Tuple[Set[str], List[Tuple[str, str]], List[str]]:
    """
    1. Получение графа зависимостей реализовать алгоритмом BFS без рекурсии.
    Строит полный граф зависимостей, обрабатывая транзитивность, фильтры и циклы.

    Returns:
        Кортеж: (Множество всех узлов, Список всех ребер, Список обнаруженных циклов)
    """
    
    all_packages: Set[str] = set()
    all_edges: List[Tuple[str, str]] = []
    # Очередь для BFS. Хранит только те пакеты, которые нужно обработать.
    queue: List[str] = [start_package]
    # Множество для отслеживания УЖЕ ДОБАВЛЕННЫХ В ГРАФ пакетов (посещенных узлов).
    visited: Set[str] = set() 
    cycles_detected: List[str] = []

    # 2. Проверка начального пакета на фильтр
    if filter_substring and filter_substring in start_package:
        return set(), [], [f"Начальный пакет '{start_package}' отфильтрован."]
    
    visited.add(start_package)
    all_packages.add(start_package)

    # Главный цикл BFS
    while queue:
        current_package = queue.pop(0)

        # Прямые зависимости. Если пакет не найден, возвращаем пустой список.
        direct_deps = repository_data.get(current_package, [])

        for dep in direct_deps:
            # 2. Не учитывать при анализе пакеты, имя которых содержит заданную подстроку.
            if filter_substring and filter_substring in dep:
                print(f"   [FILTERED] Зависимость '{dep}' отфильтрована (содержит '{filter_substring}').")
                continue # Пропускаем эту ветвь
                
            # Добавляем ребро в граф, даже если dep уже посещен.
            all_edges.append((current_package, dep))
            all_packages.add(dep)
            
            # 3. Корректно обработать случаи наличия циклических зависимостей.
            if dep in visited:
                # Обнаружен путь к уже пройденному узлу. 
                # Это означает либо цикл, либо общий предок (DAG). 
                # Для целей демонстрации сообщаем о найденном обратном ребре, 
                # но не обрабатываем его как ошибку BFS.
                if dep in all_packages: # dep уже был обнаружен
                    cycles_detected.append(f"Обратное ребро/Цикл обнаружен: {current_package} -> {dep}")
                continue # Не добавляем в очередь повторно (BFS без рекурсии)
            
            # Если пакет новый и не отфильтрован:
            visited.add(dep)
            queue.append(dep)
            
    return all_packages, all_edges, cycles_detected

def run_visualizer(package_name: str, repository_url: str, repository_mode: str, output_filename: str, filter_substring: str):
    """
    Основная логика приложения: загрузка, обход BFS и вывод.
    """
    
    # Этап 1: Вывод конфигурации
    print("--- Конфигурация инструмента визуализации графа зависимостей (Этап 3) ---")
    print(f"Имя анализируемого пакета: **{package_name}**")
    print(f"URL/Путь репозитория: **{repository_url}**")
    print(f"Режим работы с репозиторием: **{repository_mode}**")
    print(f"Имя выходного файла графа: **{output_filename}**")
    print(f"Подстрока для фильтрации пакетов: **'{filter_substring}'**")
    print("--------------------------------------------------------------------------\n")
    
    # --- Сбор данных (Этап 2) ---
    repository_data: Dict[str, List[str]] = {}
    
    if repository_mode == 'remote':
        repository_data = MOCK_REPOSITORY
        print("Используется **удаленный (remote)** режим со смоделированным репозиторием APK.")
    else: # repository_mode == 'local' (тестирование)
        print(f"Используется **тестовый (local)** режим, загрузка графа из файла: **{repository_url}**")
        repository_data = load_local_repository(repository_url)
        if not repository_data:
            print("Невозможно продолжить: Тестовый репозиторий пуст или не найден.")
            return

    if package_name not in repository_data:
        print(f"Ошибка: Начальный пакет '{package_name}' не найден в выбранном репозитории.")
        return

    # --- Основные операции (Этап 3) ---
    print(f"\nЗапуск BFS-обхода зависимостей для пакета **{package_name}**...")
    
    nodes, edges, cycles = build_dependency_graph_bfs(
        package_name,
        repository_data,
        filter_substring
    )
    
    print("\n--- Результаты построения графа ---")
    
    if filter_substring:
        print(f"Фильтрация: пакеты, содержащие **'{filter_substring}'**, исключены из дальнейшего обхода.")

    if cycles:
        print("\n**Обнаружены циклические зависимости (или обратные ребра):**")
        for cycle in cycles:
            print(f"   - {cycle}")
    else:
        print("\nЦиклические зависимости не обнаружены (в рамках обхода).")
        
    print("\n**Все обнаруженные пакеты (узлы) в графе:**")
    print(", ".join(sorted(nodes)) if nodes else "Нет пакетов (возможно, начальный пакет отфильтрован)")

    print("\n**Все обнаруженные зависимости (ребра) в графе:**")
    for source, target in edges:
        print(f"   - {source} -> {target}")

    print(f"\n(Этап 4) Граф будет сохранен в файл: **{output_filename}**")


def main():
    parser = argparse.ArgumentParser(
        description="Инструмент визуализации графа зависимостей для пакетного менеджера (Прототип, Этап 3).",
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
        help='URL репозитория (remote) или путь к файлу графа (local, по умолчанию: Alpine v3.18/main).'
    )

    parser.add_argument(
        '-m', '--mode', 
        choices=['remote', 'local'], 
        default='remote', 
        dest='repository_mode',
        help='Режим работы: "remote" (имитация APK) или "local" (тестовый файл, по умолчанию: remote).'
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
        help='Подстрока для фильтрации пакетов (пакеты, содержащие ее, исключаются).'
    )

    args = parser.parse_args()

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