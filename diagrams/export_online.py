
"""
Export PlantUML diagrams using online server
No Java installation required!
"""

import requests
import zlib
import base64
import os
from pathlib import Path

def plantuml_encode(plantuml_text):
    """Encode PlantUML text for URL using deflate encoding"""
    # Use deflate compression (raw deflate, no zlib header)
    compressed = zlib.compress(plantuml_text.encode('utf-8'), level=9)
    # Remove zlib header (2 bytes) and checksum (4 bytes)
    compressed = compressed[2:-4]

    # Custom base64 encoding for PlantUML
    b64 = base64.b64encode(compressed).decode('ascii')

    # PlantUML uses a custom base64 alphabet
    # Standard: ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/
    # PlantUML: 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_

    table = str.maketrans(
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
        '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
    )

    return b64.translate(table)

def export_diagram(puml_file, output_format='png'):
    """Export a single diagram"""
    print(f"[*] Exporting {puml_file.name}...", end=' ')

    # Read PlantUML file
    with open(puml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Encode for PlantUML server
    encoded = plantuml_encode(content)

    # Request from server
    url = f"http://www.plantuml.com/plantuml/{output_format}/{encoded}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Save output
        output_file = puml_file.with_suffix(f'.{output_format}')
        with open(output_file, 'wb') as f:
            f.write(response.content)

        file_size = len(response.content) / 1024  # KB
        print(f"OK ({file_size:.1f} KB)")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print("=" * 50)
    print("PlantUML Online Export Tool")
    print("=" * 50)
    print()

    # Find all sequence diagram files
    diagrams = sorted(Path('.').glob('sequence_uc*.puml'))

    if not diagrams:
        print("ERROR: No sequence diagram files found!")
        return

    print(f"Found {len(diagrams)} diagrams\n")

    success_count = 0
    for puml_file in diagrams:
        if export_diagram(puml_file):
            success_count += 1

    print()
    print("=" * 50)
    print(f"Export completed: {success_count}/{len(diagrams)} successful")
    print("=" * 50)
    print()
    print("PNG files are ready for your thesis report!")

if __name__ == '__main__':
    main()
