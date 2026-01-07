#!/usr/bin/env python3
"""
Script để render tất cả PlantUML diagrams sang PNG
Requires: Java + plantuml.jar
"""

import os
import subprocess
import sys
from pathlib import Path

# Configuration
PLANTUML_JAR = "plantuml.jar"  # Hoặc đường dẫn đầy đủ
OUTPUT_FORMAT = "png"  # png, svg, eps, pdf
OUTPUT_DIR = "output"

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
    """Tìm tất cả file .puml"""
    current_dir = Path(__file__).parent
    puml_files = list(current_dir.glob("*.puml"))
    return sorted(puml_files)

def render_diagram(puml_file):
    """Render 1 diagram"""
    print(f"🎨 Rendering {puml_file.name}...")

    try:
        # Tạo output directory
        output_dir = Path(__file__).parent / OUTPUT_DIR
        output_dir.mkdir(exist_ok=True)

        # Command: java -jar plantuml.jar -tpng -o output file.puml
        cmd = [
            "java",
            "-jar",
            PLANTUML_JAR,
            f"-t{OUTPUT_FORMAT}",
            "-o",
            str(output_dir),
            str(puml_file)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            output_file = output_dir / f"{puml_file.stem}.{OUTPUT_FORMAT}"
            print(f"   ✅ → {output_file}")
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

    # Check prerequisites
    if not check_java():
        return 1

    if not download_plantuml():
        return 1

    # Find PUML files
    puml_files = find_puml_files()

    if not puml_files:
        print("❌ No .puml files found in current directory")
        return 1

    print(f"\n📁 Found {len(puml_files)} diagram(s):")
    for f in puml_files:
        print(f"   • {f.name}")

    print(f"\n🚀 Starting render to {OUTPUT_FORMAT.upper()}...\n")

    # Render all
    success_count = 0
    for puml_file in puml_files:
        if render_diagram(puml_file):
            success_count += 1

    # Summary
    print()
    print("="*60)
    print(f"✅ Success: {success_count}/{len(puml_files)}")
    print(f"📂 Output directory: {OUTPUT_DIR}/")
    print("="*60)

    return 0 if success_count == len(puml_files) else 1

if __name__ == "__main__":
    sys.exit(main())