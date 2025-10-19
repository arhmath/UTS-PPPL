import os
import json
import re

INPUT_DIR = "diagrams"
OUTPUT_DIR = "output"

def parse_puml(content):
    classes = re.findall(r'class\s+(\w+)\s*\{([^}]*)\}', content)
    enums = re.findall(r'enum\s+(\w+)\s*\{([^}]*)\}', content)

    result = {
        "classes": [],
        "enums": []
    }

    for cls, body in classes:
        attributes = []
        methods = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            # atribut
            if line.startswith('-'):
                parts = line[1:].split(':')
                if len(parts) == 2:
                    attributes.append({
                        "name": parts[0].strip(),
                        "type": parts[1].strip()
                    })
            # method
            elif line.startswith('+'):
                parts = line[1:].split('(')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    param_part = parts[1].split(')')[0]
                    params = []
                    if param_part.strip():
                        for p in param_part.split(','):
                            p = p.strip()
                            if ':' in p:  # tambahkan pengecekan aman
                                pname, ptype = p.split(':')
                                params.append({
                                    "name": pname.strip(),
                                    "type": ptype.strip()
                                })
                    return_type = "void"
                    if ':' in line:
                        return_type = line.split(':')[-1].strip()
                    methods.append({
                        "name": name,
                        "parameters": params,
                        "returnType": return_type
                    })
        result["classes"].append({
            "name": cls,
            "attributes": attributes,
            "methods": methods
        })

    for enum_name, body in enums:
        values = [v.strip() for v in body.splitlines() if v.strip()]
        result["enums"].append({"name": enum_name, "values": values})

    return result


def convert_all():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for file_name in os.listdir(INPUT_DIR):
        if file_name.endswith(".puml"):
            path = os.path.join(INPUT_DIR, file_name)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            data = parse_puml(content)
            data["project"] = file_name.replace(".puml", "")

            output_path = os.path.join(OUTPUT_DIR, file_name.replace(".puml", ".json"))
            with open(output_path, 'w', encoding='utf-8') as out:
                json.dump(data, out, indent=2, ensure_ascii=False)

            print(f"✅ {file_name} berhasil dikonversi → {output_path}")

if __name__ == "__main__":
    convert_all()
