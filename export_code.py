import os

# Имя файла, куда все сохранится
output_file = 'code_context.txt'

# Папки, которые мы ИГНОРИРУЕМ (чтобы не копировать мусор)
ignore_dirs = {'.venv', 'venv', '.git', '__pycache__', '.idea', '.vscode', 'data'}

# Какие файлы копировать (только код)
include_exts = {'.py', '.txt', '.md', '.json', '.html'}

def collect_code():
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk('.'):
            # Убираем ненужные папки из обхода
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                # Проверяем расширение файла
                if any(file.endswith(ext) for ext in include_exts) and file != 'export_code.py':
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            # Красивый разделитель, чтобы я понял, где какой файл
                            outfile.write(f"\n\n{'='*20} FILE: {path} {'='*20}\n\n")
                            outfile.write(content)
                            print(f"Добавлен: {path}")
                    except Exception as e:
                        print(f"Ошибка чтения {path}: {e}")

    print(f"\n✅ Готово! Весь код сохранен в файле: {output_file}")

if __name__ == "__main__":
    collect_code()