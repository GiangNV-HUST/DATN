#!/usr/bin/env python3
"""
Script để render tất cả PlantUML diagrams sang PNG
Requires: Java + plantuml.jar

Structure:
  sources/  - chứa file .puml
  images/   - chứa file .png đã render
"""

import os
import subprocess
import sys
from pathlib import Path

# Configuration
PLANTUML_JAR = "plantuml.jar"
OUTPUT_FORMAT = "png"
SOURCES_DIR = "sources"
IMAGES_DIR = "images"

def check_java():
    """Kiểm tra Java đã cài chưa"""
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True
        )
        print("✅ Java installed")
        return True
    except FileNotFoundError:
        print("❌ Java NOT found. Please install Java first.")
        return False

def download_plantuml():
    """Download PlantUML jar nếu chưa có"""
    if os.path.exists(PLANTUML_JAR):
        print(f"✅ {PLANTUML_JAR} found")
        return True

    print(f"⬇️ Downloading {PLANTUML_JAR}...")
    try:
        import urllib.request
        url = "https://github.com/plantuml/plantuml/releases/download/v1.2024.0/plantuml-1.2024.0.jar"
        urllib.request.urlretrieve(url, PLANTUML_JAR)
        print(f"✅ Downloaded {PLANTUML_JAR}")
        return True
    except Exception as e:
        print(f"❌ Failed to download: {e}")
        print("Please download manually from: https://plantuml.com/download")
        return False

def find_puml_files():
    """Tìm tất cả file .puml trong sources/"""
    current_dir = Path(__file__).parent
    sources_path = current_dir / SOURCES_DIR
    puml_files = list(sources_path.glob("**/*.puml"))
    return sorted(puml_files)

def render_diagram(puml_file, base_dir):
    """Render 1 diagram"""
    # Tính relative path từ sources/
    rel_path = puml_file.relative_to(base_dir / SOURCES_DIR)
    output_subdir = base_dir / IMAGES_DIR / rel_path.parent

    print(f"🎨 Rendering {rel_path}...")

    try:
        # Tạo output directory
        output_subdir.mkdir(parents=True, exist_ok=True)

        # Command: java -jar plantuml.jar -tpng -o output file.puml
        cmd = [
            "java",
            "-jar",
            str(base_dir / PLANTUML_JAR),
            f"-t{OUTPUT_FORMAT}",
            "-o",
            str(output_subdir),
            str(puml_file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            output_file = output_subdir / f"{puml_file.stem}.{OUTPUT_FORMAT}"
            print(f"   ✅ → {IMAGES_DIR}/{rel_path.parent}/{puml_file.stem}.{OUTPUT_FORMAT}")
            return True
        else:
            print(f"   ❌ Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def main():
    """Main function"""
    print("="*60)
    print("PlantUML Diagram Renderer")
    print("="*60)
    print()

    base_dir = Path(__file__).parent

    # Check prerequisites
    if not check_java():
        return 1

    if not download_plantuml():
        return 1

    # Find PUML files
    puml_files = find_puml_files()

    if not puml_files:
        print(f"❌ No .puml files found in {SOURCES_DIR}/")
        return 1

    print(f"\n📁 Found {len(puml_files)} diagram(s) in {SOURCES_DIR}/")

    # Group by category
    categories = {}
    for f in puml_files:
        cat = f.parent.name
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f.name)

    for cat, files in categories.items():
        print(f"\n   📂 {cat}/ ({len(files)} files)")
        for fname in files[:5]:
            print(f"      • {fname}")
        if len(files) > 5:
            print(f"      ... and {len(files) - 5} more")

    print(f"\n🚀 Starting render to {IMAGES_DIR}/...\n")

    # Render all
    success_count = 0
    for puml_file in puml_files:
        if render_diagram(puml_file, base_dir):
            success_count += 1

    # Summary
    print()
    print("="*60)
    print(f"✅ Success: {success_count}/{len(puml_files)}")
    print(f"📂 Source: {SOURCES_DIR}/")
    print(f"📂 Output: {IMAGES_DIR}/")
    print("="*60)

    return 0 if success_count == len(puml_files) else 1

if __name__ == "__main__":
    sys.exit(main())
