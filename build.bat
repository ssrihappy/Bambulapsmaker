@echo off
chcp 65001 > nul
echo.
echo ============================================
echo   Bambulab Lapsmaker — EXE 빌드 스크립트
echo ============================================
echo.

:: 1. 의존성 설치
echo [1/4] 패키지 설치 중...
pip install -q customtkinter Pillow opencv-python paho-mqtt pyinstaller
if errorlevel 1 (
    echo ❌ 패키지 설치 실패
    pause & exit /b 1
)
echo     ✅ 패키지 준비 완료

:: 2. icon.png → icon.ico 변환
echo [2/4] 아이콘 변환 중...
python -c "from PIL import Image; img=Image.open('icon.png'); img.save('icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if errorlevel 1 (
    echo     ⚠ 아이콘 변환 실패 (계속 진행)
) else (
    echo     ✅ icon.ico 생성 완료
)

:: 3. PyInstaller 빌드
echo [3/4] PyInstaller 빌드 중... (잠시 기다려 주세요)
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "BambulapLapsmaker" ^
    --icon "icon.ico" ^
    --add-data "icon.png;." ^
    --collect-all customtkinter ^
    --hidden-import paho.mqtt.client ^
    --hidden-import paho.mqtt.publish ^
    --hidden-import cv2 ^
    app.py

if errorlevel 1 (
    echo ❌ 빌드 실패
    pause & exit /b 1
)

:: 4. 결과
echo [4/4] 완료!
echo.
echo ✅ EXE 생성 위치: dist\BambulapLapsmaker.exe
echo.
echo 사용 방법:
echo   dist\BambulapLapsmaker.exe 를 실행하세요.
echo   config.json 이 자동 생성되어 설정이 저장됩니다.
echo.
pause
