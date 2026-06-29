#pragma once
#include <Arduino.h>

// ============================================================
// Hardware — Heltec Wireless Tracker HTIT-Tracker V1.1
//            ESP32-S3FN8 + SX1262 + UC6580 GNSS + ST7735 TFT
// Fuente: Heltec official schematic + docs.heltec.org
// ============================================================

// SX1262 LoRa — HSPI/SPI3 con pines explícitos (separado del TFT)
#define LORA_NSS    8
#define LORA_SCK    9
#define LORA_MOSI   10
#define LORA_MISO   11
#define LORA_RST    12
#define LORA_BUSY   13
#define LORA_DIO1   14

// TFT LCD ST7735 160x80 — FSPI/SPI2 via TFT_eSPI (pines 41-42)
// NOTA: TFT_CS, TFT_DC, TFT_RST, TFT_MOSI, TFT_SCLK son macros de TFT_eSPI
//       Usamos PIN_TFT_* para evitar redefiniciones en nuestro código
#define PIN_TFT_MOSI  42
#define PIN_TFT_SCLK  41
#define PIN_TFT_CS    38
#define PIN_TFT_DC    40
#define PIN_TFT_RST   39
#define PIN_TFT_BL      21   // Backlight
#define PIN_TFT_BL_ON   HIGH
#define PIN_TFT_BL_OFF  LOW
#define PIN_TFT_PWR      3   // VTFT_CTRL power switch (HIGH = encendido)

// UC6580 GNSS — UART2 (RX=UC6580_TX, TX=UC6580_RX)
#define GNSS_RX_PIN   34   // ESP32 RX2 ← UC6580 TX
#define GNSS_TX_PIN   33   // ESP32 TX2 → UC6580 RX

// Botón PRG/BOOT
#define BTN_PIN      0

// LED integrado
#define LED_PIN     35

// ============================================================
// LoRa — valores por defecto
// ============================================================
#define LORA_FREQ_DEFAULT   915.0f   // MHz — banda Argentina (AU915)
#define LORA_BW_DEFAULT     125.0f   // kHz
#define LORA_SF_DEFAULT     9        // Spreading factor
#define LORA_CR_DEFAULT     7        // Coding rate 4/7
#define LORA_SYNC_WORD      0x34     // LoRaWAN public network (0x12 = red privada)
#define LORA_TX_POWER       17       // dBm
#define LORA_PREAMBLE_LEN   8
#define LORA_TCXO_VOLTAGE   1.6f     // V — TCXO de la Heltec V3

// ============================================================
// WiFi — valores por defecto
// ============================================================
#define WIFI_DEFAULT_SSID        "Exalink"
#define WIFI_DEFAULT_PASS        "daytona1309"
#define WIFI_CONNECT_TIMEOUT_MS  30000   // 30 s para conectar
#define WIFI_RECONNECT_INTERVAL  30000   // 30 s entre reintentos

// Access Point
#define AP_SSID_PREFIX   "Exalink-Gateway-"   // + 4 hex del chip ID
#define AP_IP_ADDR       "192.168.4.1"
#define AP_SUBNET        "255.255.255.0"

// ============================================================
// Servidor HTTP — valores por defecto
// ============================================================
#ifndef SERVER_DEFAULT_URL
#define SERVER_DEFAULT_URL  "https://campo.exalink.com.ar"
#endif
#define SERVER_ENDPOINT     "/api/v1/lora/ingest"
#define HTTP_TIMEOUT_MS     5000
#define LORAWAN_LISTEN_PORT_DEFAULT  6666

// ============================================================
// LoRaWAN — valores por defecto
// ============================================================
#define LORAWAN_DEFAULT_PASS  "abc1234"

// ============================================================
// Batería — Heltec Wireless Tracker V1.1
// ============================================================
#define VBAT_ADC_CTRL_PIN  37   // HIGH para habilitar divisor
#define VBAT_ADC_PIN        1   // ADC input

// ============================================================
// Login admin — valores por defecto
// ============================================================
#define ADMIN_DEFAULT_USER  "admin"
#define ADMIN_DEFAULT_PASS  "admin123"

// ============================================================
// Gateway sync
// ============================================================
#define GW_SYNC_ENDPOINT             "/api/v1/lora/gateway/sync"
#define GW_SYNC_INTERVAL_DEFAULT_MIN  1   // 1 minuto por defecto

// ============================================================
// Pairing
// ============================================================
#define PAIRING_CODE_LEN             6
#define PAIRING_TTL_MIN              10   // minutos de validez del código
#define PAIRING_DEFAULT_NAME         "Gateway sin nombre"

// ============================================================
// NVS / Preferences
// ============================================================
#define NVS_NAMESPACE       "gw_cfg"
#define NVS_KEY_SSID        "ssid"
#define NVS_KEY_PASS        "pass"
#define NVS_KEY_SERVER      "server"
#define NVS_KEY_GW_ID       "gw_id"
#define NVS_KEY_FREQ        "freq"
#define NVS_KEY_LORA_PASS    "lora_pass"
#define NVS_KEY_LISTEN_PORT  "listen_port"
#define NVS_KEY_INIT         "initialized"
#define NVS_KEY_WIFI_PENDING "wifi_pend"
#define NVS_KEY_SSID_BAK     "ssid_bak"
#define NVS_KEY_PASS_BAK     "pass_bak"
#define NVS_KEY_GW_NAME      "gw_name"
#define NVS_KEY_SYNC_INTERVAL "sync_int"
#define NVS_KEY_ADMIN_USER    "admin_u"
#define NVS_KEY_ADMIN_PASS    "admin_p"
#define NVS_KEY_IS_PAIRED     "paired"
#define NVS_KEY_PAIR_CODE     "pair_code"
#define NVS_KEY_PAIR_EXP      "pair_exp"

// ============================================================
// Misc
// ============================================================
#define SERIAL_BAUD       115200
#define WEB_SERVER_PORT   80
#define OLED_UPDATE_MS    100    // máximo rate de actualización OLED
