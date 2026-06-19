#pragma once
#include <Arduino.h>

// ============================================================
// Hardware — Heltec Wireless Tracker HTIT-Tracker V1.1
//            ESP32-S3FN8 + SX1262 + UC6580 GNSS + ST7735 TFT
// ============================================================

// SX1262 LoRa — HSPI/SPI3
#define LORA_NSS    8
#define LORA_SCK    9
#define LORA_MOSI   10
#define LORA_MISO   11
#define LORA_RST    12
#define LORA_BUSY   13
#define LORA_DIO1   14

// TFT LCD ST7735 160x80 — FSPI/SPI2
#define PIN_TFT_MOSI  42
#define PIN_TFT_SCLK  41
#define PIN_TFT_CS    38
#define PIN_TFT_DC    40
#define PIN_TFT_RST   39
#define PIN_TFT_BL      21
#define PIN_TFT_BL_ON   HIGH
#define PIN_TFT_BL_OFF  LOW
#define PIN_TFT_PWR      3

// UC6580 GNSS — UART2. V1.1 no usa enable dedicado; no forzar GPIO37.
#define GNSS_POWER_PIN   3
#define GNSS_ENABLE_PIN -1
#define GNSS_RX_PIN     33
#define GNSS_TX_PIN     34

// AHT21B — I2C
#define AHT21B_SDA_PIN    7
#define AHT21B_SCL_PIN    6

// Botón PRG (activo LOW, pullup interno)
#define BTN_PIN      0

// LED RGB integrado (WS2812B, 1 píxel)
// Comparte GPIO 35 con el reset del GPS — mantener HIGH para no resetear GNSS
#define LED_PIN         35
#define LED_NUM_PIXELS   1
#define LED_TX_MS     2000   // duración del LED en cada TX
#define GNSS_RESET_PIN   35   // GPS reset (active LOW) — shared with LED

// Batería
#define VBAT_ADC_CTRL_PIN   2   // V1.1 usa GPIO2; V1.0 no tiene pin ctrl
#define VBAT_ADC_PIN         1
#define CHRG_STAT_PIN        4   // TP4054 STAT: LOW=charging, HIGH=done/off

// ============================================================
// LoRa — parámetros (deben coincidir con el gateway)
// ============================================================
#define LORA_FREQ_DEFAULT    915.0f
#define LORA_BW_DEFAULT      125.0f
#define LORA_SF_DEFAULT      9
#define LORA_CR_DEFAULT      7
#define LORA_SYNC_WORD       0x34     // LoRaWAN red pública
#define LORA_TX_POWER        14       // dBm (20 max, 14 ahorra 75% potencia)
#define LORA_PREAMBLE_LEN    6
#define LORA_TCXO_VOLTAGE    1.6f

// ============================================================
// LoRaWAN ABP — claves derivadas de la contraseña "abc1234"
// Deben coincidir con la configuración del servidor
// ============================================================
#define LORAWAN_DEFAULT_PASS  "abc1234"

// NwkSKey = "abc1234NWK" + relleno de ceros a 16 bytes
#define LORAWAN_NWK_S_KEY \
    { 0x61,0x62,0x63,0x31,0x32,0x33,0x34,0x4E,0x57,0x4B,0,0,0,0,0,0 }

// AppSKey = "abc1234APP" + relleno de ceros a 16 bytes
#define LORAWAN_APP_S_KEY \
    { 0x61,0x62,0x63,0x31,0x32,0x33,0x34,0x41,0x50,0x50,0,0,0,0,0,0 }

// LoRaWAN FPort para datos GPS
#define LORAWAN_FPORT_GPS   1

// ============================================================
// Cliente — comportamiento
// ============================================================
#define TX_INTERVAL_MS       300000UL  // 5 minutos entre transmisiones
#define LOW_BAT_INTERVAL_MS  3600000UL // 1 hora con bateria <=10%
#define LOW_BAT_THRESHOLD    10        // % bateria para activar ahorro
#define LOW_BAT_RESTORE      15        // % bateria para restaurar normal
#define GPS_WINDOW_MS        30000UL   // tiempo de lectura GPS pre-TX (primer fix puede tardar >30s)
#define DISPLAY_ON_MS        15000UL   // duracion backlight al presionar boton (15s = ahorra bateria)
#define DISPLAY_UPDATE_MS      200     // max rate actualizacion pantalla
#define MIN_WAKE_MS           1000UL   // minimo tiempo despierto antes de dormir

// ============================================================
// WiFi — credenciales por defecto
// ============================================================
#define WIFI_DEFAULT_SSID          "Exalink"
#define WIFI_DEFAULT_PASS          "daytona1309"
#define WIFI_CONNECT_TIMEOUT_MS    20000

// ============================================================
// Servidor — API
// ============================================================
#define SERVER_DEFAULT_URL         "https://10.1.1.100:6666"
#define SERVER_LORAWAN_PASS        "abc1234"
#define HTTP_TIMEOUT_MS            5000

#define API_EQUIPMENT_ENDPOINT     "/api/lora/equipment"
#define API_INGEST_ENDPOINT        "/api/lora/ingest"
#define API_CONFIG_ENDPOINT        "/api/lora/device/config"

// ============================================================
// Dispositivo — identidad
// ============================================================
#define DEVICE_TYPE_DEFAULT        "sensor"
#define DEVICE_NAME_DEFAULT        ""
#define HW_VERSION_DEFAULT         "1.1"

// ============================================================
// NVS — almacenamiento persistente
// ============================================================
#define NVS_NAMESPACE_CLIENT       "tracker_cfg"
#define NVS_KEY_WIFI_SSID          "ssid"
#define NVS_KEY_WIFI_PASS          "pass"
#define NVS_KEY_SERVER_URL         "server"
#define NVS_KEY_DEVICE_NAME        "name"
#define NVS_KEY_DEVICE_TYPE        "dev_type"
#define NVS_KEY_REFRESH_FREQ_S     "refresh_s"
#define NVS_KEY_HW_VERSION         "hw_ver"

// ============================================================
// Misc
// ============================================================
#define SERIAL_BAUD  115200
