import os
import re

from pathlib import Path
from sys import argv
from typing import List, Set
from xml.etree import ElementTree


PROJECT_REGEX = re.compile(r"Project\(\"{\S+\"\)\s=\s\"\S+\",\s\"(\S+)\"")
NAMESPACE_WITH_BODY_REGEX = re.compile(r"namespace\s(?P<NamespaceName>\S+)\s*{(?P<Body>[\s\S]*)}")
USING_REGEX = r"using\s(?P<Using>[\S]*);";
EMPTY_LINES_REGEX = r"(\s*)(namespace)"
INDENT_REGEX = r"(?P<Indent>(\t|\ )*)\S*\s*(class|record|interface|struct|abstract|static|partial|enum)"


def parse_solution(solution_file: Path) -> List[Path]:
    with solution_file.open() as file:
        file_text = file.read()
        return [solution_file.parent.absolute() / x.replace("\\", os.sep)
            for x in re.findall(PROJECT_REGEX, file_text)]


def update_project_file(project_file: Path):
    print(f"Update {project_file}")
    tree = ElementTree.parse(project_file)
    root = tree.getroot()
    for child in root:
        tf_tags = child.findall("TargetFramework")
        if not tf_tags:
           continue 

        tf_tag = tf_tags[0]

        tf_tag.text = "net6.0"
        language_version_tag = child.find("LangVersion")
        language_version_tag.text = "10.0"

        implicit_usings_tag = ElementTree.Element("ImplicitUsings")
        implicit_usings_tag.text = "enable"
        child.append(implicit_usings_tag)
        ElementTree.indent(child, '  ', 1)

        break

    tree.write(project_file)


def update_project_files(project_file: Path):
    usings = set()
    for root, _, files in os.walk(project_file.parent):
        if f"{os.sep}obj" in root or f"{os.sep}bin" in root:
            continue

        for file in files:
            if not file.endswith(".cs"):
                continue

            update_cs_file(Path(root)/ file, usings)

    print(f"writing globals usings: {project_file.parent / 'GlobalUsings.cs'}")
    with (project_file.parent / "GlobalUsings.cs").open("w") as file_obj:
        usings_text = ""
        usings = list(usings)
        usings.sort()
        for using in usings:
            usings_text += f"global using {using};\n"
        file_obj.write(usings_text)


def update_cs_file(file: Path, project_usings: Set):
    text = ""
    with file.open() as file_obj:
        text = file_obj.read()
        indent = re.findall(INDENT_REGEX, text)
        if not indent:
            print(f"{file} is unsupported")
            return
        indent = indent[0][0]
        local_usings = re.findall(USING_REGEX, text)
        if local_usings:
            project_usings |= set(local_usings)

        text = re.sub(NAMESPACE_WITH_BODY_REGEX, rf"namespace \g<NamespaceName>;\n\g<Body>", text)
        text = re.sub(USING_REGEX, "", text)
        text = re.sub(EMPTY_LINES_REGEX, r"\2", text)
        
        lines = text.split("\n")
        for i, line in enumerate(lines):
            lines[i] = line.removeprefix(indent)

        text = "\n".join(lines)

    with file.open("w") as file_obj:
        file_obj.write(text)


def main(solution_path: Path):
    projects = parse_solution(solution_path)
    print(projects)
    for project in projects:
        if not project.exists():
            print(f"Skip {project}")
            continue
        update_project_file(project)
        update_project_files(project)


if __name__ == "__main__":
    solution_path = Path(argv[1])
    main(solution_path)
