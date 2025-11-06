import argparse
import sys

def run_visualizer(package_name, repository_url, repository_mode, output_filename, filter_substring):
    """
    Основная логика приложения. 
    На Этапе 1 только выводит полученные параметры.
    """
    
    # 3. При запуске приложения вывести все параметры, настраиваемые пользователем,
    # в формате ключ-значение.
    print("--- ⚙️ Конфигурация инструмента визуализации графа зависимостей ---")
    print(f"Имя анализируемого пакета: **{package_name}**")
    print(f"URL/Путь репозитория: **{repository_url}**")
    print(f"Режим работы с репозиторием: **{repository_mode}**")
    print(f"Имя выходного файла графа: **{output_filename}**")
    print(f"Подстрока для фильтрации пакетов: **{filter_substring}**")
    print("------------------------------------------------------------------")
    
    # Когда-нибудь Здесь в будущих этапах будет код для:
    # 1. Получения зависимостей (без использования готовых менеджеров/библиотек).
    # 2. Построения графа зависимостей.
    # 3. Визуализации и сохранения графа в файл.

def main():
    # 1. Источником настраиваемых пользователем параметров являются опции командной строки.
    parser = argparse.ArgumentParser(
        description="Минимальный прототип инструмента визуализации графа зависимостей для пакетного менеджера.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # 2. К настраиваемым параметрам относятся:
    
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
        default='https://default-repo.com', 
        dest='repository_url',
        help='URL-адрес репозитория или путь к файлу тестового репозитория (по умолчанию: https://default-repo.com).'
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
        help='Имя сгенерированного файла с изображением графа (по умолчанию: dependency_graph.png).'
    )

    parser.add_argument(
        '-f', '--filter', 
        type=str,
        default='', 
        dest='filter_substring',
        help='Подстрока для фильтрации пакетов (например, "dev-", по умолчанию: "").'
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
        print(f"\n❌ Произошла ошибка: {e}", file=sys.stderr)
        sys.exit(1)