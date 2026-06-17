"""
pre_upload.py — se ejecuta antes de cada 'pio run -t upload'

Problema: pyserial 3.5 + Python 3.14 falla con OSError[71] EPROTO al hacer
TIOCMBIC ioctl sobre /dev/ttyACM0 cuando el firmware Arduino USB CDC está activo.

Solución: parchear serial.serialposix para ignorar EPROTO en RTS/DTR, abrir el
puerto a 1200 baud (lo que dispara usb_persist_restart(RESTART_BOOTLOADER) en el
firmware ESP32-S3 Arduino), esperar 2.5 s al ROM bootloader, y dejar que esptool
conecte normalmente (el ROM bootloader sí acepta el ioctl).
"""

Import("env")          # noqa: F821  (variable inyectada por PlatformIO SCons)

import subprocess
import time

def _touch_1200(port: str) -> bool:
    import errno
    import serial
    import serial.serialposix as sp

    _orig_rts = sp.Serial._update_rts_state
    _orig_dtr = sp.Serial._update_dtr_state

    def _safe_rts(self):
        try:
            _orig_rts(self)
        except OSError as e:
            if e.errno != errno.EPROTO:
                raise

    def _safe_dtr(self):
        try:
            _orig_dtr(self)
        except OSError as e:
            if e.errno != errno.EPROTO:
                raise

    sp.Serial._update_rts_state = _safe_rts
    sp.Serial._update_dtr_state = _safe_dtr

    try:
        ser = serial.Serial(port, baudrate=1200, timeout=0.5)
        time.sleep(0.2)
        ser.close()
        return True
    except Exception as exc:
        print(f"[pre-upload] 1200-touch falló: {exc}")
        return False
    finally:
        sp.Serial._update_rts_state = _orig_rts
        sp.Serial._update_dtr_state = _orig_dtr


def before_upload(source, target, env):         # noqa: F841
    port = env.GetProjectOption("upload_port")

    # Intentar stty primero (más rápido, no necesita pyserial)
    result = subprocess.run(
        ["stty", "-F", port, "1200"],
        capture_output=True, timeout=3
    )

    if result.returncode == 0:
        print(f"[pre-upload] stty 1200-touch OK en {port}")
    else:
        # Fallback: pyserial parchado
        print(f"[pre-upload] stty falló, usando pyserial parchado en {port}")
        _touch_1200(port)

    print("[pre-upload] Esperando ROM bootloader (2.5 s)…")
    time.sleep(2.5)


env.AddPreAction("upload", before_upload)       # noqa: F821
