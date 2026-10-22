import sys


def load_config(filename):
    config = {
        "package_name": None,
        "repo_url": None,
        "repo_mode": "real",
        "package_version": "latest",
        "output_file": "graph.svg",
        "ascii_tree": "false",
        "max_depth": 3
    }

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip()

            if not clean_line or clean_line.startswith(";"):
                continue

            if "=" not in clean_line:
                continue

            name, value = clean_line.split("=", maxsplit=1)
            name = name.strip()
            value = value.strip()

            if name in config:
                config[name] = value
            else:
                continue

    return config


def validate_settings(config):
    errors = []

    if not config["package_name"]:
        errors.append("Ошибка: 'package_name' не указан в файле.")

    if not config["repo_url"] or not str(config["repo_url"]).startswith(("http://", "https://")):
        errors.append(f"Ошибка: 'repo_url' ({config['repo_url']}) должен начинаться с http:// или https://")

    mode = str(config["repo_mode"]).lower()
    if mode not in ["real", "test"]:
        errors.append(f"Ошибка: 'repo_mode' ({mode}) должен быть 'real' или 'test'.")
    else:
        config["repo_mode"] = mode

    if not config["package_version"] or "." not in config["package_version"] :
        errors.append("Ошибка: 'package_version' не указан или содержит неверное значение.")

    out_file = str(config["output_file"])
    if not out_file.endswith((".png", ".svg", ".pdf")):
        errors.append(f"Ошибка: 'output_file' ({out_file}) должен иметь расширение .png, .svg или .pdf")

    ascii_val = str(config["ascii_tree"]).lower()
    if ascii_val in ["true", "1", "yes"]:
        config["ascii_tree"] = True
    elif ascii_val in ["false", "0", "no"]:
        config["ascii_tree"] = False
    else:
        errors.append(f"Ошибка: 'ascii_tree' ({ascii_val}) должен быть true или false.")

    try:
        depth = int(config["max_depth"])
        if depth <= 0:
            errors.append("Ошибка: 'max_depth' должен быть больше 0.")
        else:
            config["max_depth"] = depth
    except (ValueError, TypeError):
        errors.append(f"Ошибка: 'max_depth' ({config['max_depth']}) должен быть целым числом.")

    if errors:
        print("\n ОБНАРУЖЕНЫ ОШИБКИ В КОНФИГУРАЦИИ:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)

    return config


settings = load_config("config.ini")

settings = validate_settings(settings)

print(f"{'Параметр':<20} | {'Значение'}")
print("-" * 45)
for key, value in settings.items():
    print(f"{key:<20} | {value}")
