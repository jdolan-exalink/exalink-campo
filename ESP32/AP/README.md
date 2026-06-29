# Exalink LoRa Gateway — Firmware MVP

Gateway LoRa/WiFi basado en **Heltec WiFi LoRa 32 V3** (ESP32-S3 + SX1262).  
Escucha paquetes LoRa y los reenvía por HTTP POST a un servidor. Incluye portal web de configuración en modo AP.

---

## Hardware objetivo

| Componente | Detalle |
|---|---|
| MCU | ESP32-S3 (240 MHz, 8 MB flash) |
| Radio LoRa | Semtech SX1262 |
| OLED | SSD1306 128×64, I2C |
| WiFi | 2.4 GHz 802.11 b/g/n |
| USB | USB-C via CP2102 (UART0) |

### Pines internos relevantes

| Señal | GPIO |
|---|---|
| LoRa NSS | 8 |
| LoRa SCK | 9 |
| LoRa MOSI | 10 |
| LoRa MISO | 11 |
| LoRa RST | 12 |
| LoRa BUSY | 13 |
| LoRa DIO1 | 14 |
| OLED SDA | 17 |
| OLED SCL | 18 |
| OLED RST | 21 |
| Vext (3.3 V ext.) | 36 |
| Botón PRG | 0 |

---

## Requisitos

- [PlatformIO](https://platformio.org/) (CLI o extensión VS Code)
- Python 3.8+
- Cable USB-C

---

## Instalación de drivers USB

La placa usa un chip **CP2102** para la comunicación USB-UART.

### Linux

El kernel incluye el driver `cp210x` desde hace años.  
Verificar que el dispositivo aparece:
```bash
ls /dev/ttyUSB*          # tras conectar la placa
dmesg | tail -20         # buscar "cp210x converter now attached"
```
Si el usuario no tiene permiso:
```bash
sudo usermod -aG dialout $USER   # cerrar sesión y volver a entrar
# o temporalmente:
sudo chmod 666 /dev/ttyUSB0
```

### Windows

1. Descargar driver CP210x: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
2. Instalar el ejecutable `.exe`.
3. El puerto aparece en Administrador de dispositivos como `COM3` (o similar).

### macOS

Desde macOS 12+ el driver está integrado. El puerto aparece como `/dev/cu.usbserial-XXXX`.

---

## Instalación de PlatformIO

```bash
pip install platformio
```
O instalar la extensión **PlatformIO IDE** en VS Code.

---

## Compilar

```bash
pio run
```

Primera compilación descarga las librerías (RadioLib, ArduinoJson, U8g2) — puede tardar ~2 min.

---

## Flashear

Con la placa conectada por USB:
```bash
pio run -t upload
```
Si falla el auto-reset, mantener el botón **PRG** (GPIO 0), presionar **RST**, soltar RST y luego soltar PRG para entrar en modo bootloader.

---

## Monitor serial

```bash
pio device monitor
```
Velocidad: **115200 baud**.  
Salida esperada en el arranque:
```
=======================================
   EXALINK LORA GATEWAY — Iniciando
=======================================
[Config] GW ID    : GW-1A2B
[Config] WiFi SSID: Exalink
[LoRa]  Inicializando SX1262 en 915.0 MHz...
[LoRa]  OK — escuchando en 915.0 MHz
[WiFi]  Conectando a 'Exalink'...
[WiFi]  Conectado. IP: 192.168.1.42
[Web]   Servidor HTTP en puerto 80
```

---

## Credenciales WiFi por defecto

| Campo | Valor |
|---|---|
| SSID | `Exalink` |
| Password | `daytona1309` |

Si esa red no está disponible, el gateway levanta automáticamente un AP de configuración.

---

## Modo AP — Portal de configuración

Si el gateway **no logra conectarse** al WiFi en **30 segundos**, activa el modo AP:

| Campo | Valor |
|---|---|
| SSID del AP | `Exalink-Gateway-XXXX` (XXXX = 4 hex del chip ID) |
| Contraseña AP | Ninguna (abierto) |
| IP del gateway | `http://192.168.4.1` |

Conectar el celular/notebook al AP y abrir `http://192.168.4.1` en el navegador.

El portal permite:
- Ver estado del gateway (WiFi, LoRa, paquetes, servidor)
- Escanear redes WiFi disponibles
- Configurar SSID, contraseña, Gateway ID, URL servidor, frecuencia LoRa
- **Guardar y Reiniciar** — el gateway se reconecta a la nueva red
- **Resetear** — borra configuración y vuelve a valores de fábrica

---

## Flujo de prueba completo

### 1. Flashear y observar serial

```bash
pio run -t upload && pio device monitor
```

### 2. Verificar OLED

Secuencia esperada:
- `EXALINK LORA GW / Iniciando...`
- `Iniciando LoRa... / 915.0 MHz`
- `Conectando WiFi: / Exalink`
- `WiFi OK / 192.168.x.x` ← éxito
- `WiFi FAIL / Iniciando AP...` ← si no conecta
- `LoRa escuchando / <IP>`

### 3. Si no conecta a Exalink

1. Conectar al WiFi `Exalink-Gateway-XXXX` desde el celular.
2. Abrir `http://192.168.4.1` en el navegador.
3. Escanear redes → seleccionar la red deseada.
4. Ingresar contraseña, URL del servidor y frecuencia.
5. Presionar **Guardar y Reiniciar**.
6. El gateway se reconecta y aparece la IP en el OLED.

### 4. Enviar paquetes LoRa de prueba

Con otro nodo LoRa (ESP32 + LoRa, Arduino + LoRa, etc.) ejecutar:

```cpp
// Nodo emisor de prueba — RadioLib, mismos parámetros que el gateway
#include <RadioLib.h>
SX1262 radio = new Module(NSS, DIO1, RST, BUSY);

void setup() {
    radio.begin(915.0, 125.0, 9, 7, 0x12, 17, 8, 1.6);
    radio.setDio2AsRfSwitch(true);
}

void loop() {
    String msg = "{\"sensor\":\"test\",\"temp\":25.3,\"hum\":60}";
    radio.transmit(msg);
    delay(10000);   // enviar cada 10 s
}
```

El gateway debe mostrar en OLED y en el serial:
```
[LoRa] PKT #1 | RSSI:-75 dBm | SNR:8.5 dB | 38 bytes
[LoRa] Payload: {"sensor":"test","temp":25.3,"hum":60}
[HTTP] POST http://192.168.1.100:8080/api/lora/ingest
```

### 5. Verificar HTTP POST

El servidor debe recibir:
```json
POST /api/lora/ingest
Content-Type: application/json

{
  "gateway_id": "GW-1A2B",
  "received_at": 45231,
  "rssi": -75,
  "snr": "8.50",
  "payload_raw": "{\"sensor\":\"test\",\"temp\":25.3,\"hum\":60}",
  "payload_json": {"sensor": "test", "temp": 25.3, "hum": 60}
}
```

Para levantar un servidor de prueba rápido con Node.js:
```bash
node -e "
const http = require('http');
http.createServer((req,res)=>{
  let body='';
  req.on('data',d=>body+=d);
  req.on('end',()=>{console.log(req.method,req.url,body);res.end('OK');});
}).listen(8080, ()=>console.log('Escuchando :8080'));
"
```

---

## Resetear configuración

Desde el portal web → botón **Resetear Configuración**.

O desde el serial / código: eliminar la partición NVS:
```bash
pio run -t erase       # borra toda la flash
pio run -t upload      # reflashear
```

---

## Estructura del proyecto

```
ExaCow/ESP32/AP/
├── platformio.ini
├── README.md
└── src/
    ├── main.cpp             # Orquestador principal
    ├── config.h             # Pines, constantes, valores por defecto
    ├── config_manager.h/cpp # NVS (Preferences) — carga/guarda config
    ├── display_manager.h/cpp# OLED SSD1306 via U8g2
    ├── wifi_manager.h/cpp   # Modo STA + AP, reconexión automática
    ├── web_portal.h/cpp     # Servidor HTTP + HTML embebido
    ├── lora_manager.h/cpp   # SX1262 via RadioLib, RX no-bloqueante
    └── http_client.h/cpp    # HTTP POST al servidor
```

---

## Librerías usadas

| Librería | Uso |
|---|---|
| [RadioLib](https://github.com/jgromes/RadioLib) | SX1262 LoRa |
| [ArduinoJson](https://arduinojson.org/) | Serialización JSON |
| [U8g2](https://github.com/olikraus/u8g2) | Display OLED SSD1306 |
| WiFi.h | Stack WiFi ESP32 (incluida en framework) |
| WebServer.h | Servidor HTTP embebido (incluida en framework) |
| HTTPClient.h | Cliente HTTP para POST (incluida en framework) |
| Preferences.h | NVS flash persistente (incluida en framework) |

---

## Roadmap — próximas features

- [ ] MQTT (soporte paralelo a HTTP)
- [ ] OTA update (ArduinoOTA o servidor propio)
- [ ] Buffer local de paquetes cuando no hay internet
- [ ] BLE provisioning (reemplaza modo AP)
- [ ] Soporte WireGuard / VPN
- [ ] Dashboard de estadísticas en el portal web
