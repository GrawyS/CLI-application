import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET


MAVEN_NS = {"m": "http://maven.apache.org/POM/4.0.0"}


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

    return config


def validate_settings(config):
    errors = []

    if not config["package_name"]:
        errors.append("Ошибка: 'package_name' не указан в файле.")
    elif ":" not in str(config["package_name"]):
        errors.append(
            f"Ошибка: 'package_name' ({config['package_name']}) должен быть в формате groupId:artifactId"
        )

    if not config["repo_url"] or not str(config["repo_url"]).startswith(("http://", "https://")):
        errors.append(f"Ошибка: 'repo_url' ({config['repo_url']}) должен начинаться с http:// или https://")

    mode = str(config["repo_mode"]).lower()
    if mode not in ["real", "test"]:
        errors.append(f"Ошибка: 'repo_mode' ({mode}) должен быть 'real' или 'test'.")
    else:
        config["repo_mode"] = mode

    if not config["package_version"] or "." not in str(config["package_version"]):
        errors.append("Ошибка: 'package_version' не указан или содержит неверное значение.")
    elif str(config["package_version"]).lower() == "latest":
        errors.append(
            "Ошибка: 'package_version' = latest не поддерживается. Укажите конкретную версию."
        )

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


# ---------- ЭТАП 2: сбор данных из Maven ----------

def build_pom_url(repo_url, group_id, artifact_id, version):
    """Строит URL к POM-файлу по правилу Maven-репозитория."""
    group_path = group_id.replace(".", "/")
    repo = repo_url.rstrip("/")
    return f"{repo}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"


def parse_pom_dependencies(pom_bytes):
    """
    Из байтов POM возвращает множество прямых зависимостей
    в виде строк 'groupId:artifactId:version'.
    Версия может отсутствовать — тогда ставим '(managed)'.
    """
    try:
        root = ET.fromstring(pom_bytes)
    except ET.ParseError as e:
        raise RuntimeError(f"POM не является корректным XML: {e}")

    deps = set()
    for dep in root.findall("m:dependencies/m:dependency", MAVEN_NS):
        g = dep.findtext("m:groupId", default="", namespaces=MAVEN_NS).strip()
        a = dep.findtext("m:artifactId", default="", namespaces=MAVEN_NS).strip()
        v = dep.findtext("m:version", default="", namespaces=MAVEN_NS).strip()
        if not v:
            v = "(managed)"
        if g and a:
            deps.add(f"{g}:{a}:{v}")
    return deps


def fetch_pom(repo_url, group_id, artifact_id, version):
    """Скачивает POM и возвращает его байты. Бросает RuntimeError при ошибках."""
    url = build_pom_url(repo_url, group_id, artifact_id, version)
    print(f"\nСкачиваю POM: {url}")

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(
                f"Пакет {group_id}:{artifact_id}:{version} не найден в репозитории (404)."
            )
        raise RuntimeError(f"Ошибка HTTP {e.code} при скачивании POM.")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ошибка сети: не удалось подключиться к {repo_url} ({e.reason}).")


def load_package_dependencies(repo_url, package_name, version):
    """
    Аналог load_packages из статьи, но для Maven.
    Возвращает словарь { 'groupId:artifactId:version': set('dep1', 'dep2', ...) }
    для ОДНОГО пакета (прямые зависимости). На этапе 3 этот словарь
    будет расширяться при обходе DFS.
    """
    group_id, artifact_id = package_name.split(":", 1)
    pom_bytes = fetch_pom(repo_url, group_id, artifact_id, version)
    deps = parse_pom_dependencies(pom_bytes)

    node = f"{group_id}:{artifact_id}:{version}"
    return {node: deps}


def main():
    settings = load_config("config.ini")
    settings = validate_settings(settings)

    if settings["repo_mode"] == "test":
        print("[этап 2] Тестовый режим будет реализован на этапе 3. Пропускаю.")
        return

    try:
        graph = load_package_dependencies(
            settings["repo_url"],
            settings["package_name"],
            settings["package_version"],
        )
    except RuntimeError as e:
        print(f"\n{e}")
        sys.exit(1)

    root_node = next(iter(graph))
    deps = graph[root_node]

    print(f"Прямые зависимости {root_node}:")
    if not deps:
        print("  (нет прямых зависимостей)")
    else:
        for d in sorted(deps):
            print(f"  - {d}")


if __name__ == "__main__":
    main()