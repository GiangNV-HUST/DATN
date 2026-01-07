@echo off
echo Exporting all sequence diagrams...

REM Export to PNG (300 DPI for print quality)
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc1_xac_thuc.puml
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc2_dang_ky_canh_bao.puml
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc3_subscription.puml
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc4_loc_co_phieu.puml
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc5_truy_van.puml
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc6_phan_tich.puml
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc7_chart.puml
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc8_tu_van_dau_tu.puml
java -jar plantuml.jar -tpng -charset UTF-8 sequence_uc9_discovery.puml

echo.
echo Export completed! Check the PNG files in this folder.
pause
