"""
BambuLapsmaker — GUI Application
=====================================
Bambu Lab P1 프린터 타임랩스 자동 캡처 & 영상 변환 앱
"""

import os
import sys
import json
import re
import glob
import ssl
import queue
import threading
import datetime

import cv2
import paho.mqtt.client as mqtt

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk

# ─── 경로 설정 ───────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE  = os.path.join(BASE_DIR, "config.json")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")

# PyInstaller 번들 내부 리소스용 경로 헬퍼
def _res(rel: str) -> str:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return os.path.join(meipass, rel)
    return os.path.join(BASE_DIR, rel)

ICON_PATH = _res("app_icon.png")

# ─── 상수 ────────────────────────────────────────────────────────────────────
APP_NAME    = "BambuLapsmaker"
APP_VERSION = "1.0"
MQTT_PORT   = 8883

DEFAULT_CONFIG = {
    "printer_ip":     "",
    "printer_serial": "",
    "access_code":    "",
    "tapo_ip":        "",
    "tapo_user":      "",
    "tapo_pass":      "",
    "tapo_stream":    "stream1",
    "fps":            60,
    "width":          3840,
}

# ─── 색상 팔레트 ─────────────────────────────────────────────────────────────
BAMBU_GREEN   = "#00AE68"
BAMBU_GREEN_H = "#00c97a"
BG_DARK       = "#0f172a"
BG_PANEL      = "#1e293b"
BG_CARD       = "#0f172a"
BG_INPUT      = "#1e293b"
TEXT_MAIN     = "#f1f5f9"
TEXT_DIM      = "#94a3b8"
RED           = "#ef4444"
RED_H         = "#dc2626"
ORANGE        = "#f97316"
BORDER        = "#334155"

# ─── CustomTkinter 테마 ───────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


# ─────────────────────────────────────────────────────────────────────────────
class BambuLapsmaker(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1020x720")
        self.minsize(900, 620)
        self.configure(fg_color=BG_DARK)

        # 윈도우 아이콘
        try:
            _ico = Image.open(ICON_PATH)
            self._icon_photo = ImageTk.PhotoImage(_ico)
            self.wm_iconphoto(True, self._icon_photo)
        except Exception:
            pass

        # 앱 상태
        self.cfg              = self._load_config()
        self.mqtt_client      = None
        self.mqtt_connected   = False
        self._connecting      = False
        self.capture_count    = 0
        self.current_layer    = -1
        self._skip_first_layer = True   # 연결 직후 첫 레이어 이벤트는 스킵
        self.snap_lock        = threading.Lock()
        self.log_queue        = queue.Queue()
        self.video_running    = False
        self._blink_job       = None

        self._build_ui()
        self._poll_log()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._log(f"▶ {APP_NAME} v{APP_VERSION} 시작됨")

    # ─── Config ──────────────────────────────────────────────────────────────
    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def _save_config(self):
        try:
            fps   = int(self.var_fps.get() or 60)
            width = int(self.var_width.get() or 3840)
        except ValueError:
            messagebox.showerror("오류", "FPS와 Width는 숫자로 입력하세요.")
            return

        data = {
            "printer_ip":     self.var_ip.get().strip(),
            "printer_serial": self.var_serial.get().strip(),
            "access_code":    self.var_access.get().strip(),
            "tapo_ip":        self.var_tapo_ip.get().strip(),
            "tapo_user":      self.var_tapo_user.get().strip(),
            "tapo_pass":      self.var_tapo_pass.get().strip(),
            "tapo_stream":    self.var_stream.get(),
            "fps":            fps,
            "width":          width,
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._log("✅ Preset 저장 완료 — 다음 실행 시 자동 로드됩니다.")
        except Exception as e:
            self._log(f"❌ 설정 저장 실패: {e}")

    # ─── UI 구성 ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── 타이틀 바
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        try:
            img = ctk.CTkImage(Image.open(ICON_PATH), size=(34, 34))
            ctk.CTkLabel(hdr, image=img, text="").pack(side="left", padx=(18, 10), pady=12)
        except Exception:
            pass

        ctk.CTkLabel(
            hdr, text=APP_NAME,
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=TEXT_MAIN,
        ).pack(side="left", pady=12)

        ctk.CTkLabel(
            hdr, text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_DIM,
        ).pack(side="left", padx=(8, 0), pady=12)

        # ── 본문
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=14)
        body.columnconfigure(0, weight=0, minsize=310)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # 왼쪽 패널
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._build_device_card(left)
        self._build_camera_card(left)
        self._build_video_card(left)
        self._build_preset_button(left)

        # 오른쪽 패널
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        self._build_connection_card(right)
        self._build_log_card(right)
        self._build_action_card(right)

    # ── 카드 헬퍼
    def _card(self, parent: ctk.CTkFrame, title: str):
        outer = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=12)
        outer.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            outer, text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=BAMBU_GREEN,
        ).pack(anchor="w", padx=16, pady=(12, 2))
        sep = ctk.CTkFrame(outer, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=(0, 8))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 14))
        return inner

    def _row(self, parent, label: str, var: ctk.StringVar, show=""):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=4)
        ctk.CTkLabel(
            f, text=label, width=108, anchor="w",
            font=ctk.CTkFont(size=12), text_color=TEXT_DIM,
        ).pack(side="left")
        e = ctk.CTkEntry(
            f, textvariable=var, show=show,
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
            text_color=TEXT_MAIN, height=33, corner_radius=7,
        )
        e.pack(side="left", fill="x", expand=True)
        return e

    # ── 카드들
    def _build_device_card(self, parent):
        c   = self._card(parent, "🖨  기기 설정")
        cfg = self.cfg
        self.var_ip     = ctk.StringVar(value=cfg["printer_ip"])
        self.var_serial = ctk.StringVar(value=cfg["printer_serial"])
        self.var_access = ctk.StringVar(value=cfg["access_code"])
        self._row(c, "Printer IP",   self.var_ip)
        self._row(c, "Serial No.",   self.var_serial)
        self._row(c, "Access Code",  self.var_access, show="*")

    def _build_camera_card(self, parent):
        c   = self._card(parent, "📷  카메라 설정 (Tapo RTSP)")
        cfg = self.cfg
        self.var_tapo_ip   = ctk.StringVar(value=cfg["tapo_ip"])
        self.var_tapo_user = ctk.StringVar(value=cfg["tapo_user"])
        self.var_tapo_pass = ctk.StringVar(value=cfg["tapo_pass"])
        self.var_stream    = ctk.StringVar(value=cfg["tapo_stream"])
        self._row(c, "Camera IP",  self.var_tapo_ip)
        self._row(c, "Username",   self.var_tapo_user)
        self._row(c, "Password",   self.var_tapo_pass, show="*")

        sf = ctk.CTkFrame(c, fg_color="transparent")
        sf.pack(fill="x", pady=4)
        ctk.CTkLabel(
            sf, text="Stream", width=108, anchor="w",
            font=ctk.CTkFont(size=12), text_color=TEXT_DIM,
        ).pack(side="left")
        ctk.CTkSegmentedButton(
            sf, values=["stream1", "stream2"],
            variable=self.var_stream,
            fg_color=BG_INPUT,
            selected_color=BAMBU_GREEN,
            selected_hover_color=BAMBU_GREEN_H,
            unselected_color=BG_INPUT,
            unselected_hover_color="#334155",
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=12),
            height=33,
        ).pack(side="left")

    def _build_video_card(self, parent):
        c   = self._card(parent, "🎬  영상 설정")
        cfg = self.cfg
        self.var_fps   = ctk.StringVar(value=str(cfg["fps"]))
        self.var_width = ctk.StringVar(value=str(cfg["width"]))
        self._row(c, "FPS",       self.var_fps)
        self._row(c, "Width (px)", self.var_width)

    def _build_preset_button(self, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(
            f, text="💾  설정 저장 (Preset)",
            command=self._save_config,
            fg_color=BAMBU_GREEN, hover_color=BAMBU_GREEN_H,
            text_color="#000000", font=ctk.CTkFont(size=13, weight="bold"),
            height=42, corner_radius=10,
        ).pack(fill="x")

    def _build_connection_card(self, parent):
        outer = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=12)
        outer.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            outer, text="🔌  Bambu Lab 연결",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=BAMBU_GREEN,
        ).pack(anchor="w", padx=16, pady=(12, 2))
        sep = ctk.CTkFrame(outer, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=(0, 10))

        row = ctk.CTkFrame(outer, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 10))

        # 상태 인디케이터
        stat = ctk.CTkFrame(row, fg_color="transparent")
        stat.pack(side="left", fill="y")

        self.lbl_dot = ctk.CTkLabel(
            stat, text="●",
            font=ctk.CTkFont(size=24),
            text_color=RED,
        )
        self.lbl_dot.pack(side="left")

        self.lbl_status = ctk.CTkLabel(
            stat, text="연결 끊김",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_DIM,
        )
        self.lbl_status.pack(side="left", padx=(8, 0))

        self.btn_connect = ctk.CTkButton(
            row, text="연결",
            command=self._toggle_connect,
            fg_color=BAMBU_GREEN, hover_color=BAMBU_GREEN_H,
            text_color="#000000", font=ctk.CTkFont(size=13, weight="bold"),
            height=38, width=110, corner_radius=8,
        )
        self.btn_connect.pack(side="right")

        # 레이어 / 캡처 카운터
        self.lbl_layer = ctk.CTkLabel(
            outer,
            text="레이어: —    캡처: 0장",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_DIM,
        )
        self.lbl_layer.pack(anchor="w", padx=16, pady=(0, 12))

    def _build_log_card(self, parent):
        outer = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=12)
        outer.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(outer, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        ctk.CTkLabel(
            hdr, text="📋  로그 모니터",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=BAMBU_GREEN,
        ).pack(side="left")
        ctk.CTkButton(
            hdr, text="지우기",
            command=self._clear_log,
            width=58, height=24,
            fg_color=BORDER, hover_color="#475569",
            text_color=TEXT_DIM, font=ctk.CTkFont(size=11),
            corner_radius=6,
        ).pack(side="right")

        sep = ctk.CTkFrame(outer, fg_color=BORDER, height=1)
        sep.grid(row=0, column=0, sticky="ew", padx=16, pady=(38, 0))

        self.log_box = ctk.CTkTextbox(
            outer,
            fg_color=BG_CARD,
            text_color="#6ee7b7",
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            border_color=BORDER, border_width=1,
            wrap="word",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 14))
        self.log_box.configure(state="disabled")

    def _build_action_card(self, parent):
        outer = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=12)
        outer.grid(row=2, column=0, sticky="ew")

        ctk.CTkLabel(
            outer, text="⚙  작업",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=BAMBU_GREEN,
        ).pack(anchor="w", padx=16, pady=(12, 2))
        sep = ctk.CTkFrame(outer, fg_color=BORDER, height=1)
        sep.pack(fill="x", padx=16, pady=(0, 10))

        btns = ctk.CTkFrame(outer, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(0, 10))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        self.btn_video = ctk.CTkButton(
            btns, text="🎬  동영상 만들기",
            command=self._make_video,
            fg_color=BAMBU_GREEN, hover_color=BAMBU_GREEN_H,
            text_color="#000000", font=ctk.CTkFont(size=13, weight="bold"),
            height=44, corner_radius=9,
        )
        self.btn_video.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btns, text="🗑  사진 삭제",
            command=self._delete_photos,
            fg_color=BG_INPUT, hover_color=RED_H,
            text_color=TEXT_MAIN, font=ctk.CTkFont(size=13, weight="bold"),
            height=44, corner_radius=9,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # 진행 바
        self.progress_bar = ctk.CTkProgressBar(
            outer, fg_color=BORDER, progress_color=BAMBU_GREEN,
            height=6, corner_radius=3,
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 14))
        self.progress_bar.set(0)

        self.lbl_progress = ctk.CTkLabel(
            outer, text="",
            font=ctk.CTkFont(size=11), text_color=TEXT_DIM,
        )
        self.lbl_progress.pack(anchor="e", padx=16, pady=(0, 10))

    # ─── 로그 ────────────────────────────────────────────────────────────────
    def _log(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{ts}] {msg}")

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_box.configure(state="normal")
                self.log_box.insert("end", msg + "\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(80, self._poll_log)

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ─── 연결 ────────────────────────────────────────────────────────────────
    def _toggle_connect(self):
        if self.mqtt_connected:
            self._disconnect()
        elif not self._connecting:
            self._connect()

    def _connect(self):
        ip     = self.var_ip.get().strip()
        serial = self.var_serial.get().strip()
        code   = self.var_access.get().strip()

        if not ip or not serial or not code:
            messagebox.showerror("오류", "Printer IP, Serial No., Access Code를 모두 입력하세요.")
            return

        self._connecting = True
        self._set_status("connecting")
        self._log(f"MQTT 연결 시도 중... → {ip}:{MQTT_PORT}")
        threading.Thread(
            target=self._mqtt_thread, args=(ip, serial, code), daemon=True
        ).start()

    def _mqtt_thread(self, ip: str, serial: str, code: str):
        try:
            topic  = f"device/{serial}/report"
            client = mqtt.Client()
            client.username_pw_set("bblp", code)

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            client.tls_set_context(ctx)

            def on_connect(c, ud, flags, rc):
                self._connecting = False
                if rc == 0:
                    c.subscribe(topic)
                    self.mqtt_connected    = True
                    self._skip_first_layer = True   # 재연결 시에도 첫 레이어 스킵 초기화
                    self.after(0, lambda: self._set_status("connected"))
                    self.after(0, lambda: self._log(f"✅ MQTT 연결 성공 — {ip}"))
                    self.after(0, lambda: self._log(f"   구독 토픽: {topic}"))
                else:
                    self.mqtt_connected = False
                    self.after(0, lambda: self._set_status("disconnected"))
                    self.after(0, lambda: self._log(f"❌ MQTT 연결 실패 (rc={rc})"))

            def on_disconnect(c, ud, rc):
                self.mqtt_connected = False
                self._connecting    = False
                self.after(0, lambda: self._set_status("disconnected"))
                if rc != 0:
                    self.after(0, lambda: self._log(f"⚠ 연결 예기치 않게 끊김 (rc={rc})"))

            def on_message(c, ud, msg):
                self._handle_message(msg)

            client.on_connect    = on_connect
            client.on_disconnect = on_disconnect
            client.on_message    = on_message

            client.connect(ip, MQTT_PORT, keepalive=60)
            self.mqtt_client = client
            client.loop_forever()

        except Exception as e:
            self._connecting    = False
            self.mqtt_connected = False
            self.after(0, lambda: self._set_status("disconnected"))
            self.after(0, lambda: self._log(f"❌ 연결 오류: {e}"))

    def _disconnect(self):
        if self.mqtt_client:
            try:
                self.mqtt_client.disconnect()
            except Exception:
                pass
            self.mqtt_client = None
        self.mqtt_connected = False
        self._connecting    = False
        self._set_status("disconnected")
        self._log("🔌 연결 해제됨.")

    def _set_status(self, state: str):
        self._stop_blink()
        if state == "connected":
            self.lbl_dot.configure(text_color=BAMBU_GREEN)
            self.lbl_status.configure(text="연결됨  (MQTT)", text_color=BAMBU_GREEN)
            self.btn_connect.configure(
                text="연결 해제", state="normal",
                fg_color=RED, hover_color=RED_H,
                text_color=TEXT_MAIN,
            )
        elif state == "connecting":
            self.lbl_dot.configure(text_color=ORANGE)
            self.lbl_status.configure(text="연결 중...", text_color=ORANGE)
            self.btn_connect.configure(
                text="연결 중...", state="disabled",
                fg_color=BORDER, hover_color=BORDER,
                text_color=TEXT_DIM,
            )
            self._start_blink()
        else:
            self.lbl_dot.configure(text_color=RED)
            self.lbl_status.configure(text="연결 끊김", text_color=TEXT_DIM)
            self.btn_connect.configure(
                text="연결", state="normal",
                fg_color=BAMBU_GREEN, hover_color=BAMBU_GREEN_H,
                text_color="#000000",
            )

    def _start_blink(self):
        def _blink():
            if not self._connecting:
                return
            cur = self.lbl_dot.cget("text_color")
            nxt = ORANGE if cur == BG_DARK else BG_DARK
            self.lbl_dot.configure(text_color=nxt)
            self._blink_job = self.after(500, _blink)
        _blink()

    def _stop_blink(self):
        if self._blink_job:
            self.after_cancel(self._blink_job)
            self._blink_job = None

    # ─── MQTT 메시지 처리 ────────────────────────────────────────────────────
    def _handle_message(self, msg):
        try:
            payload    = json.loads(msg.payload.decode("utf-8"))
            print_info = payload.get("print", {})
            layer = print_info.get("layer_num") or print_info.get("mc_layer_num")
            if layer is None:
                return
            layer = int(layer)
            with self.snap_lock:
                if layer != self.current_layer and layer > 0:
                    self.current_layer = layer

                    # 연결 직후 첫 번째로 감지되는 레이어는 스킵 (임의의 잔여 레이어)
                    if self._skip_first_layer:
                        self._skip_first_layer = False
                        self.after(0, lambda l=layer: self._log(
                            f"⏭  레이어 {l:04d} 감지 — 첫 레이어 스킵 (저장 안 함)"
                        ))
                        return

                    self.after(0, lambda l=layer: self._log(
                        f"📸 레이어 {l:04d} 감지 — 스냅샷 캡처 시작"
                    ))
                    threading.Thread(
                        target=self._grab_snapshot, args=(layer,), daemon=True
                    ).start()
        except Exception:
            pass

    def _grab_snapshot(self, layer_num: int):
        tapo_ip   = self.var_tapo_ip.get().strip()
        tapo_user = self.var_tapo_user.get().strip()
        tapo_pass = self.var_tapo_pass.get().strip()
        stream    = self.var_stream.get()
        rtsp_url  = f"rtsp://{tapo_user}:{tapo_pass}@{tapo_ip}/{stream}"

        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        filename = os.path.join(SNAPSHOT_DIR, f"layer_{layer_num:04d}.jpg")

        try:
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                self.after(0, lambda: self._log(
                    f"  ❌ Layer {layer_num:04d} — RTSP 연결 실패 (URL/계정 확인)"
                ))
                return
            for _ in range(3):
                cap.grab()
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                self.after(0, lambda: self._log(
                    f"  ❌ Layer {layer_num:04d} — 프레임 읽기 실패"
                ))
                return

            cv2.imwrite(filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            self.capture_count += 1
            h, w = frame.shape[:2]
            cnt  = self.capture_count
            self.after(0, lambda: self._log(
                f"  ✅ Layer {layer_num:04d} 저장 완료 ({w}×{h})"
            ))
            self.after(0, lambda: self.lbl_layer.configure(
                text=f"레이어: {layer_num}    캡처: {cnt}장"
            ))
        except Exception as e:
            self.after(0, lambda: self._log(
                f"  ❌ Layer {layer_num:04d} 오류: {e}"
            ))

    # ─── 동영상 만들기 ────────────────────────────────────────────────────────
    def _make_video(self):
        if self.video_running:
            return

        pattern = os.path.join(SNAPSHOT_DIR, "layer_*.jpg")
        files   = glob.glob(pattern)
        if not files:
            messagebox.showwarning(
                "이미지 없음",
                f"snapshots 폴더에 layer_XXXX.jpg 파일이 없습니다.\n({SNAPSHOT_DIR})",
            )
            return

        try:
            fps   = int(self.var_fps.get())
            width = int(self.var_width.get())
        except ValueError:
            messagebox.showerror("오류", "FPS와 Width는 숫자로 입력하세요.")
            return

        images = sorted(files, key=lambda p: int(re.search(r"layer_(\d+)", p).group(1)))
        out    = os.path.join(BASE_DIR, "timelapse.mp4")

        self._log(f"🎬 동영상 생성 시작 — {len(images)}장 | {fps} fps | width={width}")
        self.video_running = True
        self.btn_video.configure(state="disabled", text="생성 중...")
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="")

        threading.Thread(
            target=self._make_video_thread,
            args=(images, out, fps, width),
            daemon=True,
        ).start()

    def _make_video_thread(self, images, out_path, fps, width):
        try:
            first = cv2.imread(images[0])
            if first is None:
                self.after(0, lambda: self._log("❌ 첫 번째 이미지를 열 수 없습니다."))
                return

            oh, ow = first.shape[:2]
            if width and width != ow:
                out_w = width + (width % 2)
                out_h = int(oh * width / ow)
                out_h += out_h % 2
            else:
                out_w, out_h = ow, oh

            self.after(0, lambda: self._log(
                f"   출력 해상도: {out_w}×{out_h}  |  길이 ≈ {len(images)/fps:.1f}초"
            ))

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(out_path, fourcc, fps, (out_w, out_h))
            if not writer.isOpened():
                self.after(0, lambda: self._log("❌ VideoWriter 초기화 실패"))
                return

            total     = len(images)
            milestone = max(1, total // 10)   # 10% 단위로 로그
            last_frame = None                  # 마지막 프레임 보관용

            for i, path in enumerate(images, 1):
                frame = cv2.imread(path)
                if frame is None:
                    continue
                if (out_w, out_h) != (frame.shape[1], frame.shape[0]):
                    frame = cv2.resize(frame, (out_w, out_h),
                                       interpolation=cv2.INTER_LANCZOS4)
                writer.write(frame)
                last_frame = frame             # 마지막 성공 프레임 기억

                pct = i / total
                self.after(0, lambda p=pct: self.progress_bar.set(p))
                if i % milestone == 0 or i == total:
                    self.after(0, lambda ii=i, t=total, p=pct: (
                        self._log(f"   [{ii}/{t}] {p*100:.0f}%"),
                        self.lbl_progress.configure(
                            text=f"{ii}/{t}  ({p*100:.0f}%)"
                        ),
                    ))

            # 마지막 프레임을 1초(fps 프레임)만큼 정지 화면으로 추가
            if last_frame is not None:
                freeze_frames = max(1, fps)
                for _ in range(freeze_frames):
                    writer.write(last_frame)
                self.after(0, lambda: self._log(
                    f"   ⏸  마지막 프레임 {freeze_frames}프레임({fps}fps=1초) 정지 추가"
                ))

            writer.release()

            if os.path.exists(out_path):
                mb = os.path.getsize(out_path) / 1024 / 1024
                self.after(0, lambda: self._log(
                    f"✅ 완료! → timelapse.mp4  ({mb:.1f} MB)"
                ))
                self.after(0, lambda: self.lbl_progress.configure(
                    text="완료!"
                ))
            else:
                self.after(0, lambda: self._log("❌ 출력 파일이 생성되지 않았습니다."))

        except Exception as e:
            self.after(0, lambda: self._log(f"❌ 오류: {e}"))
        finally:
            self.video_running = False
            self.after(0, lambda: self.btn_video.configure(
                state="normal", text="🎬  동영상 만들기"
            ))

    # ─── 사진 삭제 ───────────────────────────────────────────────────────────
    def _delete_photos(self):
        pattern = os.path.join(SNAPSHOT_DIR, "layer_*.jpg")
        files   = glob.glob(pattern)
        if not files:
            messagebox.showinfo("알림", "삭제할 사진 파일이 없습니다.")
            return

        if not messagebox.askyesno(
            "사진 삭제 확인",
            f"snapshots 폴더의 사진 파일 {len(files)}장을 삭제합니다.\n"
            "영상 파일(.mp4)은 삭제되지 않습니다.\n\n계속하시겠습니까?",
        ):
            return

        deleted, failed = 0, 0
        for f in files:
            try:
                os.remove(f)
                deleted += 1
            except Exception as e:
                self._log(f"  ⚠ 삭제 실패: {os.path.basename(f)} — {e}")
                failed += 1

        self._log(f"🗑  사진 삭제 완료 — {deleted}장 삭제" +
                  (f", {failed}장 실패" if failed else ""))
        self.capture_count = 0
        self.current_layer = -1
        self.lbl_layer.configure(text="레이어: —    캡처: 0장")

    # ─── 종료 ────────────────────────────────────────────────────────────────
    def _on_close(self):
        self._disconnect()
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = BambuLapsmaker()
    app.mainloop()


if __name__ == "__main__":
    main()
