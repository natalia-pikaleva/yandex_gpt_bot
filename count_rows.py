import os


def count_lines_in_file(filepath):
    count = 0
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line_strip = line.strip()
            if line_strip and not line_strip.startswith('#'):
                count += 1
    return count


def count_lines_in_dir(directory):
    total_lines = 0
    exclude_dirs = {'.venv', '__pycache__', '.git', 'node_modules'}
    for root, dirs, files in os.walk(directory):
        # Удаляем из обхода директории, которые нужно исключить
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                total_lines += count_lines_in_file(path)
    return total_lines



if __name__ == "__main__":
    project_path = r"C:\Users\deva0\PycharmProjects\consultant_bot"
    print(f"Общее количество строк кода: {count_lines_in_dir(project_path)}")
