@echo off
chcp 65001 >nul
echo ========================================
echo PlantUML Diagram Export Tool
echo ========================================
echo.

REM Check if plantuml.jar exists
if not exist plantuml.jar (
    echo [1/2] Downloading PlantUML...
    echo.
    powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/plantuml/plantuml/releases/download/v1.2024.3/plantuml-1.2024.3.jar' -OutFile 'plantuml.jar'}"

    if errorlevel 1 (
        echo ERROR: Failed to download PlantUML
        echo Please download manually from: https://plantuml.com/download
        pause
        exit /b 1
    )
    echo Download completed!
    echo.
) else (
    echo [✓] plantuml.jar already exists
    echo.
)

echo [2/2] Exporting diagrams to PNG...
echo.

REM Export all diagrams
for %%f in (sequence_uc*.puml) do (
    echo Exporting %%f...
    java -jar plantuml.jar -tpng -charset UTF-8 "%%f"
)

echo.
echo ========================================
echo ✓ Export completed!
echo ========================================
echo.
echo PNG files created:
dir /b sequence_uc*.png 2>nul

if errorlevel 1 (
    echo.
    echo WARNING: No PNG files found. Export may have failed.
    echo Make sure Java is installed: java -version
) else (
    echo.
    echo You can now insert these PNG files into your thesis report.
)

echo.
pause
