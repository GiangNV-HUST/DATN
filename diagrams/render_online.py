#!/usr/bin/env python3
"""
Render PlantUML diagrams using online server for better Vietnamese font support
"""

import requests
import zlib
import base64
from pathlib import Path
import time

PLANTUML_SERVER = "http://www.plantuml.com/plantuml/png/"
SOURCES_DIR = "sources"
IMAGES_DIR = "images"

def encode_plantuml(plantuml_text):
    """Encode PlantUML text for URL"""
    # Compress with zlib
    compressed = zlib.compress(plantuml_text.encode('utf-8'))[2:-4]
    # Base64 encode with PlantUML alphabet
    return base64.b64encode(compressed).decode('ascii').translate(
        str.maketrans(
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
            '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
        )
    ).rstrip('=')

def render_diagram_online(puml_file, base_dir):
    """Render diagram using PlantUML online server"""
    rel_path = puml_file.relative_to(base_dir / SOURCES_DIR)
    output_subdir = base_dir / IMAGES_DIR / rel_path.parent
    output_file = output_subdir / f"{puml_file.stem}.png"

    print(f"[RENDER] {rel_path}...")

    try:
        # Read PlantUML source
        with open(puml_file, 'r', encoding='utf-8') as f:
            plantuml_text = f.read()

        # Encode for URL
        encoded = encode_plantuml(plantuml_text)
        url = f"{PLANTUML_SERVER}{encoded}"

        # Download rendered image
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            # Create output directory
            output_subdir.mkdir(parents=True, exist_ok=True)

            # Save PNG
            with open(output_file, 'wb') as f:
                f.write(response.content)

            print(f"   [OK] -> {output_file.relative_to(base_dir)}")
            return True
        else:
            print(f"   [ERROR] Server returned {response.status_code}")
            return False

    except Exception as e:
        print(f"   [ERROR] {e}")
        return False

def find_puml_files(base_dir):
    """Find all .puml files in sources/"""
    sources_path = base_dir / SOURCES_DIR
    return sorted(sources_path.glob("**/*.puml"))

def main():
    print("="*60)
    print("PlantUML Online Renderer (Vietnamese Font Support)")
    print("="*60)
    print()

    base_dir = Path(__file__).parent
    puml_files = find_puml_files(base_dir)

    if not puml_files:
        print(f"[ERROR] No .puml files found in {SOURCES_DIR}/")
        return 1

    print(f"[INFO] Found {len(puml_files)} diagram(s)")

    # Group by category
    categories = {}
    for f in puml_files:
        cat = f.parent.name
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f.name)

    for cat, files in categories.items():
        print(f"\n   [{cat}] ({len(files)} files)")

    print(f"\n[START] Rendering via {PLANTUML_SERVER}...\n")

    success_count = 0
    for i, puml_file in enumerate(puml_files, 1):
        if render_diagram_online(puml_file, base_dir):
            success_count += 1

        # Be nice to the server
        if i < len(puml_files):
            time.sleep(0.5)

    print()
    print("="*60)
    print(f"[DONE] Success: {success_count}/{len(puml_files)}")
    print(f"[SOURCE] {SOURCES_DIR}/")
    print(f"[OUTPUT] {IMAGES_DIR}/")
    print("="*60)

    return 0 if success_count == len(puml_files) else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
