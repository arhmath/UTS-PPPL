import os
import json
import re

INPUT_DIR = "diagrams"
OUTPUT_FILE = "output/lost_found_system.json"

# Mapping file ke domain
DOMAIN_MAPPING = {
    "main_classdiagram": "userManagement",
    "pengelolaanbarang": "pengelolaanLaporan",
    "adminstrasipelaporan": "administrasiPelaporan",
    "administrasipelaporan": "administrasiPelaporan"
}

# Deskripsi domain
DOMAIN_DESCRIPTIONS = {
    "userManagement": "Sistem untuk mengelola data pengguna dan autentikasi.",
    "pengelolaanLaporan": "Sistem untuk mengelola laporan barang hilang, temuan, dan klaim.",
    "administrasiPelaporan": "Sistem untuk administrasi, statistik, dan arsip laporan."
}

# MAPPING BARU: Atribut yang harus dipetakan ke Enum
ENUM_ATTRIBUTE_MAPPING = {
    "statusLaporan": "Laporanhilang",
    "statusBarang": "Laporantemuan",
    "statusKlaim": "Klaimbarang",
    "statusSesi": "Usersession",
    "role": "Role", # Enum kustom
    "periode": "PeriodeLaporanStatistik" # Enum kustom
}


def parse_puml(content):
    # Parse Class Diagram
    classes = re.findall(r'class\s+(\w+)\s*\{([^}]*)\}', content, re.IGNORECASE)
    # Tetap mempertahankan parsing enum eksplisit (jika ada)
    enums = re.findall(r'enum\s+(\w+)\s*\{([^}]*)\}', content, re.IGNORECASE)

    class_data = []
    enum_data = []

    # Parse classes
    for cls, body in classes:
        attributes = []
        
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Parse attributes (dimulai dengan -)
            if line.startswith('-'):
                parts = line[1:].split(':')
                if len(parts) == 2:
                    attr_name = parts[0].strip()
                    attr_type = parts[1].strip()
                    
                    # Konversi tipe data ke format standar
                    type_mapping = {
                        "String": "String",
                        "Integer": "Integer",
                        "Boolean": "Boolean",
                        "Date": "Date",
                        "DateTime": "Timestamp",
                        "Float": "Float"
                    }
                    
                    # Cek apakah ID
                    if attr_name.endswith("ID"):
                        attr_type = "ID"
                    else:
                        attr_type = type_mapping.get(attr_type, attr_type)
                    
                    attributes.append({"name": attr_name, "type": attr_type})
        
        class_data.append({
            "name": cls, 
            "attributes": attributes
        })

    # Parse enums
    for enum_name, body in enums:
        values = [v.strip() for v in body.splitlines() if v.strip()]
        enum_data.append({"name": enum_name, "values": values})

    # Parse Statechart
    transitions = []
    states_set = set()
    transition_pattern = re.compile(r'^\s*(\S+?)\s*-->\s*(\S+?)\s*(?::\s*(.*))?$', re.MULTILINE)
    matches = transition_pattern.findall(content)

    for source, target, label in matches:
        states_set.add(source.strip())
        states_set.add(target.strip())
        event = label.strip() if label else None
        transitions.append({
            "source": source.strip(),
            "target": target.strip(),
            "event": event
        })

    initial_state = "[*]" if "[*]" in states_set else None
    if initial_state:
        states_set.discard("[*]")
    states = sorted(list(states_set))
    
    return {
        "classes": class_data,
        "enums": enum_data,
        "states": states,
        "transitions": transitions,
        "initialState": initial_state
    }

def get_domain_from_filename(filename):
    """Dapatkan domain berdasarkan nama file"""
    base_name = filename.replace(".puml", "").lower()
    
    # Cek setiap key di DOMAIN_MAPPING
    for key, domain in DOMAIN_MAPPING.items():
        if key in base_name:
            return domain
    return None

def convert_all():
    output_dir = os.path.dirname(OUTPUT_FILE)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Struktur output akhir
    final_output = {
        "modelName": "Lost and Found Information System",
        "version": "1.0",
        "domains": [],
        "enumerations": [],
        "classes": [],
        "statecharts": []
    }

    # Set untuk tracking domain yang sudah ditambahkan
    added_domains = set()
    
    # Dictionary untuk menyimpan semua enum (untuk cek referensi)
    all_enums = {}

    # --- FASE 1: Proses Class Diagrams & Statecharts ---
    print("🔄 Memproses file .puml...\n")
    for file_name in sorted(os.listdir(INPUT_DIR)):
        if not file_name.endswith(".puml"):
            continue
            
        path = os.path.join(INPUT_DIR, file_name)
        # print(f"📄 Processing: {file_name}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        data = parse_puml(content)
        domain = get_domain_from_filename(file_name)
        
        # Jika file adalah class diagram
        if domain and (file_name.startswith("class_") or file_name.startswith("main_")):
            # Tambah domain jika belum ada
            if domain not in added_domains:
                final_output["domains"].append({
                    "name": domain,
                    "description": DOMAIN_DESCRIPTIONS.get(domain, "")
                })
                added_domains.add(domain)
                # print(f"   └─ ✅ Domain '{domain}' added")
            
            # Simpan enums eksplisit ke dictionary (untuk cek referensi nanti)
            for enum in data["enums"]:
                all_enums[enum["name"]] = enum["values"]
            
            # Tambahkan classes (akan diproses ulang di FASE 2)
        
        # Jika file adalah state diagram
        elif "state" in file_name:
            # Ekstrak nama statechart (contoh: 'state_laporanhilang' -> 'Laporanhilang')
            state_name = file_name.replace("state_", "").replace(".puml", "")
            state_name = ''.join(word.capitalize() for word in state_name.split('_'))
            
            final_output["statecharts"].append({
                "name": state_name,
                "states": data["states"],
                "transitions": data["transitions"],
                "initialState": data["initialState"]
            })
            # print(f"   └─ ✅ Statechart '{state_name}' added")

    # --- FASE 2: Membuat Enumerations dari Statecharts dan Kustom ---
    
    # 1. Tambahkan Enum dari Statecharts
    for statechart in final_output["statecharts"]:
        enum_name = statechart["name"]
        # Hapus state transisi "[*]" jika ada
        values = [s for s in statechart["states"] if s != "[*]"]
        all_enums[enum_name] = values
    
    # 2. Tambahkan Enum Kustom (berdasarkan Notes/Logic)
    all_enums["Role"] = ["mahasiswa", "dosen", "staff", "petugas_keamanan"]
    all_enums["PeriodeLaporanStatistik"] = ["Bulanan", "Semesteran", "Tahunan"]
    
    print("\n🔄 Memproses enumerations dan classes...")
    
    # Tambahkan semua enums ke output
    for enum_name, enum_values in all_enums.items():
        final_output["enumerations"].append({
            "name": enum_name,
            "choices": enum_values
        })
        print(f"📋 Enum '{enum_name}' added with {len(enum_values)} choices")
    
    # --- FASE 3: Proses Kelas dengan Pemetaan Enum ---

    # Proses ulang file untuk menambahkan classes dengan format yang benar
    for file_name in sorted(os.listdir(INPUT_DIR)):
        if not file_name.endswith(".puml"):
            continue
        
        if not (file_name.startswith("class_") or file_name.startswith("main_")):
            continue
            
        path = os.path.join(INPUT_DIR, file_name)
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        data = parse_puml(content)
        domain = get_domain_from_filename(file_name)
        
        if not domain:
            continue
        
        # Tambahkan classes
        for cls in data["classes"]:
            class_obj = {
                "domainRef": domain,
                "className": cls["name"],
                "attributes": []
            }
            
            # Proses setiap attribute
            for attr in cls["attributes"]:
                attr_obj = {
                    "name": attr["name"],
                    "type": attr["type"]
                }
                
                # Cek apakah attribute name harus menggunakan enum (Status/Role)
                enum_ref_name_by_name = ENUM_ATTRIBUTE_MAPPING.get(attr["name"])
                
                # Cek berdasarkan nama atribut atau tipe data (untuk enum eksplisit)
                if enum_ref_name_by_name in all_enums:
                    attr_obj["type"] = "Enumerated"
                    attr_obj["enumRef"] = enum_ref_name_by_name
                elif attr["type"] in all_enums:
                    attr_obj["type"] = "Enumerated"
                    attr_obj["enumRef"] = attr["type"]
                
                class_obj["attributes"].append(attr_obj)
            
            final_output["classes"].append(class_obj)

    # Simpan ke file JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        json.dump(final_output, out, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"✅ Konversi berhasil!")
    print(f"📦 Total domains: {len(final_output['domains'])}")
    print(f"📦 Total enumerations: {len(final_output['enumerations'])}")
    print(f"📦 Total classes: {len(final_output['classes'])}")
    print(f"📦 Total statecharts: {len(final_output['statecharts'])}")
    print(f"💾 Output: {OUTPUT_FILE}")
    print(f"{'='*60}")

if __name__ == "__main__":
    convert_all()