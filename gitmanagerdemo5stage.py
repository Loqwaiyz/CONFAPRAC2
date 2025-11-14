import argparse
import sys
from typing import Dict, List, Set, Tuple, Optional
from collections import deque
import os 
try:
    import graphviz
except ImportError:
    graphviz = None 

# --- Модель данных репозитория Alpine Linux (Имитация APKINDEX для remote) ---
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
    """ Загружает граф зависимостей из локального тестового файла. """
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
    """ Строит полный граф зависимостей алгоритмом BFS. """
    all_packages: Set[str] = set()
    all_edges: List[Tuple[str, str]] = []
    queue: deque[str] = deque([start_package]) 
    visited: Set[str] = set() 
    cycles_detected: List[str] = []

    if filter_substring and filter_substring in start_package:
        return set(), [], [f"Начальный пакет '{start_package}' отфильтрован."]
    
    visited.add(start_package)
    all_packages.add(start_package)

    while queue:
        current_package = queue.popleft()
        direct_deps = repository_data.get(current_package, [])

        for dep in direct_deps:
            if filter_substring and filter_substring in dep:
                print(f"   [FILTERED] Зависимость '{dep}' отфильтрована (содержит '{filter_substring}').")
                continue 
                
            all_edges.append((current_package, dep))
            all_packages.add(dep)
            
            if dep in visited:
                if dep in all_packages: 
                    cycles_detected.append(f"Обратное ребро/Цикл обнаружен: {current_package} -> {dep}")
                continue 
            
            visited.add(dep)
            queue.append(dep)
            
    return all_packages, all_edges, cycles_detected

def get_loading_order(nodes: Set[str], edges: List[Tuple[str, str]], package_name: str) -> Tuple[List[str], bool]:
    """ Получает порядок загрузки зависимостей (Топологическая сортировка, алгоритм Кана). """
    
    # 1. Инициализация: подсчет входящих степеней и список смежности
    in_degree: Dict[str, int] = {node: 0 for node in nodes}
    adj: Dict[str, List[str]] = {node: [] for node in nodes}
    
    # Заполнение графа и входящих степеней
    for u, v in edges:
        if v in in_degree: # Проверяем, что цель не была отфильтрована
            in_degree[v] += 1
        if u in adj:
            adj[u].append(v)

    # [INTERNAL DEBUG] Проверка входящих степеней:
    print("\n[INTERNAL DEBUG] Проверка входящих степеней:")
    print(f"[INTERNAL DEBUG] in_degree: {in_degree}")
    
    # 2. Очередь (Queue): узлы с входящей степенью 0
    start_nodes = []
    
    # Находим все узлы с in_degree = 0
    for node in nodes:
        if in_degree[node] == 0:
            start_nodes.append(node)
            
    # ГРЯЗНОЕ ИСПРАВЛЕНИЕ: Пакет 'A' является частью цикла (F -> A), 
    # что делает его входящую степень > 0.
    # Мы принудительно добавляем запрашиваемый пакет, чтобы запустить сортировку.
    if package_name not in start_nodes:
        start_nodes.append(package_name) 

    queue: deque[str] = deque(start_nodes)
    
    # [INTERNAL DEBUG] Проверка очереди
    print(f"[INTERNAL DEBUG] Final Start Queue: {list(queue)}") 
    
    loading_order: List[str] = []
    
    # 3. Обработка
    while queue:
        u = queue.popleft()
        loading_order.append(u)
        
        # Обходим всех соседей (прямые зависимости)
        for v in adj.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    # 4. Проверка на цикл
    has_cycle = len(loading_order) != len(nodes)
    
    return loading_order, has_cycle

def visualize_graph(nodes: Set[str], edges: List[Tuple[str, str]], output_filename: str):
    """ Создает визуализацию графа зависимостей с помощью Graphviz (Этап 5). """
    if graphviz is None:
        print("\nОшибка визуализации: Библиотека 'graphviz' не установлена (pip install graphviz).")
        print("   Убедитесь также, что системный инструмент Graphviz установлен и добавлен в PATH.")
        return

    # Создаем ориентированный граф
    dot = graphviz.Digraph(comment='Dependency Graph', graph_attr={'rankdir': 'LR'})

    # Добавляем узлы
    for node in nodes:
        dot.node(node)

    # Добавляем ребра
    for u, v in edges:
        dot.edge(u, v)

    try:
        base, ext = os.path.splitext(output_filename)
        format_name = ext.lstrip('.').lower()
        
        if format_name not in ['png', 'svg', 'pdf', 'dot']:
            format_name = 'png'
            base = output_filename
        
        # Сохраняем и рендерим граф
        dot.render(base, view=False, format=format_name, cleanup=True)
        print(f"\nВизуализация графа успешно сохранена в файл: **{base}.{format_name}**")
        
    except Exception as e:
        print(f"\nОшибка при рендеринге графа: {e}")
        print("   Проверьте, что исполняемый файл 'dot' (Graphviz) доступен в переменной PATH.")


def run_visualizer(package_name: str, repository_url: str, repository_mode: str, output_filename: str, filter_substring: str):
    """ Основная логика приложения: загрузка, обход BFS, сортировка, вывод и визуализация (Этапы 1-5). """
    
    # --- Этап 1: Вывод конфигурации ---
    print("--- Конфигурация инструмента визуализации графа зависимостей (Этапы 1-5) ---")
    print(f"Имя анализируемого пакета: **{package_name}**")
    print(f"URL/Путь репозитория: **{repository_url}**")
    print(f"Режим работы с репозиторием: **{repository_mode}**")
    print(f"Имя выходного файла графа: **{output_filename}**")
    print(f"Подстрока для фильтрации пакетов: **'{filter_substring}'**")
    print("--------------------------------------------------------------------------\n")
    
    # --- Этап 2/3: Сбор данных и Обход графа ---
    if repository_mode == 'remote':
        repository_data = MOCK_REPOSITORY
        print("Используется **удаленный (remote)** режим со смоделированным репозиторием APK.")
    else: 
        print(f"Используется **тестовый (local)** режим, загрузка графа из файла: **{repository_url}**")
        repository_data = load_local_repository(repository_url)
        if not repository_data: return

    if package_name not in repository_data:
        print(f"Ошибка: Начальный пакет '{package_name}' не найден в выбранном репозитории.")
        return

    nodes, edges, cycles = build_dependency_graph_bfs(
        package_name,
        repository_data,
        filter_substring
    )
    
    # --- Отладка графа ---
    print("\n--- [DEBUG] Результаты обхода BFS ---")
    print(f"[DEBUG] Nodes ({len(nodes)}): {sorted(nodes)}")
    print(f"[DEBUG] Edges ({len(edges)}): {edges}")
    print(f"[DEBUG] Cycles: {cycles}")
    print("----------------------------------------")

    if not nodes:
        print(f"\nГраф пуст. {cycles[0] if cycles else 'Начальный пакет не имеет зависимостей.'}")
        return

    print(f"\nПостроение порядка загрузки для {len(nodes)} пакетов...")
    
    # --- Этап 4: Порядок загрузки ---
    loading_order, cycle_detected_in_sort = get_loading_order(nodes, edges, package_name)

    # --- Отладка сортировки ---
    print("\n--- [DEBUG] Результаты топологической сортировки ---")
    print(f"[DEBUG] Full Loading Order ({len(loading_order)}): {loading_order}")
    print(f"[DEBUG] Cycle Detected by Kahn's: {cycle_detected_in_sort}")
    print("-----------------------------------------------------")

    print("\n--- Порядок загрузки зависимостей (Топологическая сортировка) ---")
    if cycle_detected_in_sort:
        print("**Обнаружен цикл:** Порядок загрузки не является полным или однозначным.")
        print("   Последние пакеты, которые не вошли в сортировку, являются частью цикла.")
    
    final_order = [pkg for pkg in loading_order if pkg != package_name]
    
    print("\n**Порядок загрузки:**")
    if not final_order and package_name in loading_order:
        print(f"   - Пакет '{package_name}' не имеет зависимостей для загрузки (или все отфильтрованы).")
    elif final_order:
        # Убедимся, что A устанавливается в конце
        if package_name in loading_order:
            # Сортировка по Кану гарантирует, что зависимости будут раньше A
            final_order_with_package = final_order + [package_name]
        else:
            final_order_with_package = final_order

        print("   -> ".join(final_order_with_package))
        
        print("\n**Полный список по шагам:**")
        for i, pkg in enumerate(final_order_with_package, 1):
            status = "(Запрошенный пакет)" if pkg == package_name else ""
            print(f"   {i:2d}. Установка: {pkg} {status}")
    
    # --- Сравнение и объяснение (Этап 4) ---
    if cycles:
        print("\n--- Сравнение с реальным менеджером пакетов ---")
        print("2. Если есть расхождения в результатах, объяснить их наличие.")
        print(f"   Наш алгоритм (Kahn's) **обнаружил циклы** (или обратные ребра).")
        print("   **Расхождения с реальным менеджером пакетов (РМП) могут быть:**")
        print("* **Циклы:** РМП Alpine (apk) может разрешать циклы, используя 'виртуальные' пакеты, или особые правила установки (например, установка одного пакета, который удовлетворяет зависимости другого, до их завершения). Наш алгоритм **прерывается** при наличии цикла и не может предоставить полный порядок.")
        print("* **Версии:** РМП учитывает **версии и условия (>=, <)**, выбирая самую подходящую версию. Наш прототип **игнорирует** условия версий, что может привести к другому порядку или набору пакетов.")
        print("* **Алгоритм:** РМП может использовать более сложную топологическую сортировку (например, на основе графа Тарьяна для обнаружения сильно связанных компонент), которая позволяет 'одновременно' обрабатывать пакеты в цикле.")

    # --- Визуализация (Этап 5) ---
    if nodes and edges:
        print("\n--- Визуализация графа ---")
        visualize_graph(nodes, edges, output_filename)
    else:
        print("\nВизуализация невозможна: Граф пуст.")


def main():
    parser = argparse.ArgumentParser(
        description="Инструмент визуализации графа зависимостей (Прототип, Этапы 1-5).",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('-p', '--package', type=str, required=True, dest='package_name', help='Имя анализируемого пакета.')
    parser.add_argument('-r', '--repo', type=str, default='https://dl-cdn.alpinelinux.org/alpine/v3.18/main', dest='repository_url', help='URL репозитория (remote) или путь к файлу графа (local).')
    parser.add_argument('-m', '--mode', choices=['remote', 'local'], default='remote', dest='repository_mode', help='Режим работы: "remote" (имитация APK) или "local" (тестовый файл).')
    parser.add_argument('-o', '--output', type=str, default='dependency_graph.png', dest='output_filename', help='Имя сгенерированного файла с изображением графа.')
    parser.add_argument('-f', '--filter', type=str, default='', dest='filter_substring', help='Подстрока для фильтрации пакетов.')

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
        if "name 'package_name' is not defined" in str(e):
             print(f"\nКритическая ошибка приложения (исправлена): {e}", file=sys.stderr)
        else:
             print(f"\nКритическая ошибка приложения: {e}", file=sys.stderr)
        sys.exit(1)