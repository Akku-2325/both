import os

# Название итогового файла
output_file = "all_bot_code.txt"
# Расширения файлов, которые собираем
extensions = ('.py', '.env', '.json') 
# Папки, которые игнорируем (чтобы не собрать тысячи файлов библиотек)
ignore_dirs = {'venv', '.git', '__pycache__', 'env'}

with open(output_file, 'w', encoding='utf-8') as outfile:
    for root, dirs, files in os.walk('.'):
        # Пропускаем ненужные папки
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if file.endswith(extensions) and file != output_file and file != 'export_code.py':
                path = os.path.join(root, file)
                outfile.write(f"\n{'='*50}\n")
                outfile.write(f"FILE: {path}\n")
                outfile.write(f"{'='*50}\n\n")
                try:
                    with open(path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"Could not read file: {e}")
                outfile.write("\n")

print(f"Готово! Весь код собран в файл: {output_file}")