<div align="center">

<img src="app_icon.ico" width="100" alt="BambuLapsmaker Icon"/>

# Bambulab Lapsmaker

**Bambu Lab P1 시리즈 3D 프린터를 위한 타임랩스 자동 캡처 & 영상 변환 툴**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green)](#license)
[![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet)](https://github.com/TomSchimansky/CustomTkinter)

</div>

---

## 📖 개요

**Bambulab Lapsmaker**는 Bambu Lab P1 시리즈 프린터의 MQTT 신호를 수신해 레이어가 바뀔 때마다 Tapo 카메라의 RTSP 스트림에서 자동으로 스냅샷을 캡처하고, 촬영된 이미지를 고화질 타임랩스 MP4 영상으로 변환하는 로컬 데스크탑 앱입니다.

별도 서버나 클라우드 없이 **로컬 네트워크만으로** 동작하며, 단일 EXE 파일로 배포됩니다.

---

## ✨ 주요 기능

| 기능 | 설명 |
|---|---|
| 🔌 **MQTT 자동 연결** | Bambu Lab 프린터에 TLS 암호화로 연결, 레이어 변경 이벤트 실시간 감지 |
| 📸 **레이어별 스냅샷** | 레이어가 바뀔 때마다 Tapo 카메라 RTSP 스트림에서 자동 캡처 |
| 🎬 **타임랩스 영상 변환** | 캡처된 이미지를 H.264 MP4로 변환 (FPS·해상도 직접 설정 가능) |
| 💾 **Preset 저장** | 모든 설정을 `config.json`에 저장, 재실행 시 자동 복원 |
| 📋 **실시간 로그 모니터** | 타임스탬프 포함 이벤트 로그, 원클릭 지우기 |
| 🗑 **사진 일괄 삭제** | 영상 파일은 유지하고 스냅샷 JPG만 선택 삭제 |
| 🖥 **단일 EXE 배포** | PyInstaller로 빌드, Python 없이 실행 가능 |

---

## 🖼 스크린샷

> *(앱 실행 화면)*

```
┌──────────────────────────────────────────────────────────┐
│  🎥 Bambulab Lapsmaker  v1.0                             │
├─────────────────────────┬────────────────────────────────┤
│  🖨 기기 설정            │  🔌 Bambu Lab 연결              │
│  Printer IP  [      ]   │  ● 연결됨 (MQTT)   [연결 해제]  │
│  Serial No.  [      ]   │  레이어: 042   캡처: 42장       │
│  Access Code [******]   ├────────────────────────────────┤
├─────────────────────────┤  📋 로그 모니터         [지우기] │
│  📷 카메라 설정           │  [09:12:01] ✅ MQTT 연결 성공   │
│  Camera IP   [      ]   │  [09:12:15] 📸 레이어 0001 감지 │
│  Username    [      ]   │  [09:12:15]   ✅ 저장 완료      │
│  Password    [******]   │  ...                            │
│  Stream  [stream1][2]   ├────────────────────────────────┤
├─────────────────────────┤  [🎬 동영상 만들기] [🗑 사진 삭제]│
│  🎬 영상 설정            │  ████████████░░░░  42/50 (84%) │
│  FPS         [  60  ]   └────────────────────────────────┘
│  Width (px)  [ 3840 ]
├─────────────────────────┤
│  [💾 설정 저장 (Preset)] │
└─────────────────────────┘
```

---

## 🛠 사전 준비

### 하드웨어

- **Bambu Lab P1P / P1S** (MQTT LAN Mode 지원 모델)
- **TP-Link Tapo 카메라** (RTSP 스트림 지원 모델)
- 동일 로컬 네트워크 환경

### 프린터 정보 확인

| 항목 | 확인 경로 |
|---|---|
| **IP 주소** | 프린터 스크린 → Network / 공유기 관리 페이지 |
| **Serial No.** | 프린터 스크린 → Settings → Device → Serial Number |
| **Access Code** | 프린터 스크린 → Settings → LAN Mode |

### Tapo RTSP 활성화

```
Tapo 앱 → 카메라 선택 → 설정(⚙) → 고급 설정 → RTSP 스트림 → ON
(카메라 전용 계정/비밀번호도 같은 화면에서 설정)
```

---

## 🚀 설치 및 실행

### 방법 A — EXE 직접 실행 (권장)

1. [Releases](../../releases) 페이지에서 `BambulapLapsmaker.exe` 다운로드
2. `icon.png`를 EXE와 같은 폴더에 위치
3. `BambulapLapsmaker.exe` 실행

> 첫 실행 시 `config.json`이 자동 생성됩니다.

---

### 방법 B — 소스 코드 직접 실행

**1. 저장소 클론**

```bash
git clone https://github.com/ssrihappy/Bambulapsmaker.git
cd Bambulapsmaker
```

**2. 패키지 설치**

```bash
pip install -r requirements.txt
```

**3. 앱 실행**

```bash
python app.py
```

---

### 방법 C — EXE 직접 빌드

```bash
build.bat
```

빌드 완료 후 `dist/BambuLapsmaker.exe` 생성됩니다.

> 내부적으로 아래 명령어를 실행합니다.
> ```bash
> pyinstaller --noconfirm --onefile --windowed \
>   --name "BambuLapsmaker" \
>   --icon "icon.ico" \
>   --add-data "icon.png;." \
>   --collect-all customtkinter \
>   app.py
> ```

---

## ⚙ 설정 항목

앱 내에서 설정 후 **💾 설정 저장 (Preset)** 을 누르면 `config.json`에 저장됩니다.

```json
{
  "printer_ip":     "192.168.0.xx",
  "printer_serial": "01P123123123123",
  "access_code":    "12345678",
  "tapo_ip":        "192.168.0.xx",
  "tapo_user":      "your_rtsp_user",
  "tapo_pass":      "your_rtsp_pass",
  "tapo_stream":    "stream1",
  "fps":            60,
  "width":          3840
}
```

| 키 | 설명 | 기본값 |
|---|---|---|
| `printer_ip` | 프린터 로컬 IP | `192.168.0.xx` |
| `printer_serial` | 프린터 시리얼 번호 | — |
| `access_code` | LAN Mode 8자리 코드 | — |
| `tapo_ip` | Tapo 카메라 IP | `192.168.0.xx` |
| `tapo_user` | RTSP 계정 | — |
| `tapo_pass` | RTSP 비밀번호 | — |
| `tapo_stream` | 화질 (`stream1` 고화질 / `stream2` 저화질) | `stream1` |
| `fps` | 타임랩스 FPS | `60` |
| `width` | 출력 영상 가로 해상도 (px) | `3840` |

---

## 📁 프로젝트 구조

```
bambulab-lapsmaker/
│
├── app.py               # GUI 메인 앱
│
├── app_icon.png             # 앱 아이콘
├── requirements.txt     # Python 패키지 목록
├── build.bat            # EXE 빌드 스크립트 (Windows)
│
├── config.json          # 저장된 설정 (자동 생성)
├── snapshots/           # 캡처된 이미지 저장 폴더 (자동 생성)
│   ├── layer_0001.jpg
│   ├── layer_0002.jpg
│   └── ...
└── timelapse.mp4        # 생성된 영상 (자동 생성)
```

---

## 🔄 동작 흐름

```
Bambu Lab P1 프린터
       │
       │  MQTT (TLS, Port 8883)
       │  토픽: device/{SERIAL}/report
       ▼
  layer_num 변경 감지
       │
       │  별도 스레드로 즉시 실행
       ▼
  Tapo 카메라 RTSP 접속
  rtsp://user:pass@ip/stream1
       │
       │  프레임 3장 버퍼 플러시 → 최신 프레임 캡처
       ▼
  snapshots/layer_XXXX.jpg 저장
       │
       ▼  (인쇄 완료 후)
  [🎬 동영상 만들기] 클릭
       │
       ▼
  timelapse.mp4 생성
  (OpenCV VideoWriter, mp4v 코덱)
```

---

## 🖥 CLI 독립 실행 (선택 사항)

GUI 없이 터미널에서도 사용 가능합니다.

**캡처만 실행**

```bash
python layer_capture.py
```

> `layer_capture.py` 상단의 설정값을 직접 수정 후 실행

**영상 변환만 실행**

```bash
python make_video.py --fps 30 --width 1920
python make_video.py --dir ./snapshots --out timelapse.mp4 --fps 60 --width 3840
```

| 인자 | 설명 | 기본값 |
|---|---|---|
| `--dir` | 스냅샷 폴더 경로 | `./snapshots` |
| `--out` | 출력 파일명 | `timelapse.mp4` |
| `--fps` | 초당 프레임 수 | `60` |
| `--width` | 출력 가로 해상도 | `3840` |

---

## 📦 의존 패키지

```
customtkinter >= 5.2.0   # 모던 다크 UI
Pillow        >= 10.0.0  # 아이콘 처리
opencv-python >= 4.8.0   # RTSP 캡처 & 영상 인코딩
paho-mqtt     >= 1.6.1   # MQTT 클라이언트
pyinstaller   >= 6.0.0   # EXE 빌드 (개발용)
```

---

## ❓ 자주 묻는 질문

<details>
<summary><b>연결 버튼을 눌러도 계속 "연결 중..."이 됩니다</b></summary>

- 프린터 스크린에서 **LAN Mode**가 활성화되어 있는지 확인하세요.
- IP 주소, 시리얼, Access Code가 정확한지 확인하세요.
- 방화벽이 **포트 8883 (MQTT over TLS)** 을 차단하고 있지 않은지 확인하세요.
- 프린터와 PC가 **동일한 네트워크**에 있는지 확인하세요.

</details>

<details>
<summary><b>스냅샷 캡처 시 "RTSP 연결 실패"가 표시됩니다</b></summary>

- Tapo 앱에서 RTSP 스트림이 **ON** 상태인지 확인하세요.
- Camera IP, Username, Password가 올바른지 확인하세요.
- RTSP URL을 VLC 등으로 직접 테스트해 보세요:
  ```
  rtsp://username:password@camera_ip/stream1
  ```

</details>

<details>
<summary><b>동영상 만들기 버튼을 눌렀을 때 파일이 생성되지 않습니다</b></summary>

- `snapshots/` 폴더에 `layer_XXXX.jpg` 파일이 있는지 확인하세요.
- FPS와 Width가 올바른 숫자인지 확인하세요.
- 출력 경로(`timelapse.mp4`)에 쓰기 권한이 있는지 확인하세요.

</details>

<details>
<summary><b>EXE 빌드 시 antivirus가 차단합니다</b></summary>

PyInstaller로 빌드된 EXE는 일부 백신에서 오탐(False Positive)이 발생할 수 있습니다.  
소스 코드를 직접 확인하거나, 백신 예외 처리 후 사용하세요.

</details>

---

## 📄 License

MIT License — 자유롭게 사용, 수정, 배포 가능합니다.

---

<div align="center">

Made with ❤️ for the Bambu Lab community [https://makerworld.com/ko/@Pharm/upload]

</div>
