#include "lora_client.h"
#include "config.h"
#include <ArduinoJson.h>
#include <string.h>

// ─── LoRa raw transmission ─────────────────────────────────────────────────────

LoRaClient::LoRaClient()
    : _spi(HSPI)
    , _radio(new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY, _spi))
    , _freq(LORA_FREQ_DEFAULT)
    , _devAddr(0)
    , _fcnt(0)
{
}

bool LoRaClient::begin(float freq) {
    _freq = freq;

    uint64_t mac = ESP.getEfuseMac();
    _devAddr = (uint32_t)(mac >> 32) ^ (uint32_t)(mac & 0xFFFFFFFF);

    _spi.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

    Serial.printf("[LoRa] Inicializando SX1262 en %.1f MHz (TX)...\n", freq);
    Serial.printf("[LoRa] DevAddr: %08X\n", _devAddr);

    int state = _radio.begin(
        freq,
        LORA_BW_DEFAULT,
        LORA_SF_DEFAULT,
        LORA_CR_DEFAULT,
        LORA_SYNC_WORD,
        LORA_TX_POWER,
        LORA_PREAMBLE_LEN,
        LORA_TCXO_VOLTAGE
    );

    if (state != RADIOLIB_ERR_NONE) {
        Serial.printf("[LoRa] ERROR begin(): %d\n", state);
        return false;
    }

    _radio.setDio2AsRfSwitch(true);

    Serial.printf("[LoRa] OK — %.1f MHz SF%d BW%.0fkHz sync=0x%02X\n",
                  freq, LORA_SF_DEFAULT, LORA_BW_DEFAULT, LORA_SYNC_WORD);
    return true;
}

bool LoRaClient::send(const GpsData& gps, bool gpsModuleSeen, uint8_t battery,
                       float temperatureC, float humidityPct, bool gpsFresh,
                       bool charging, uint32_t bootCount, uint32_t wakeMs,
                       const MpuReading& mpu0, const MpuReading& mpu1,
                       const String& pairingCode) {
    // Construir payload JSON compacto
    DynamicJsonDocument doc(576);
    doc["d"]  = "raw-" + getDevAddrHex();
    doc["tp"] = "animal";
    if (gps.valid) {
        doc["lt"] = gps.lat;
        doc["ln"] = gps.lon;
    } else {
        doc["lt"] = nullptr;
        doc["ln"] = nullptr;
    }
    doc["g"] = gpsFresh ? 1 : 0;
    doc["gm"] = gpsModuleSeen ? 1 : 0;
    doc["gq"] = gps.fixQuality;
    doc["gs"] = gps.satellites;
    doc["hd"] = serialized(String(gps.hdop, 1));
    doc["ga"] = serialized(String(gps.altitudeM, 1));
    doc["gv"] = serialized(String(gps.speedKmh, 1));
    doc["gc"] = serialized(String(gps.courseDeg, 1));
    doc["age"] = gps.valid ? (uint32_t)(gps.age_ms / 1000UL) : 0;
    if (gps.timeValid) {
        doc["gt"] = (uint32_t)gps.utcHour * 10000UL
                  + (uint32_t)gps.utcMin * 100UL
                  + (uint32_t)gps.utcSec;
    }
    if (!isnan(temperatureC)) doc["t"] = temperatureC;
    else doc["t"] = nullptr;
    if (!isnan(humidityPct)) doc["h"] = humidityPct;
    else doc["h"] = nullptr;
    doc["b"]  = battery;
    doc["ch"] = charging ? 1 : 0;
    doc["wb"] = bootCount;
    doc["wt"] = wakeMs;
    doc["hv"] = HW_VERSION_DEFAULT;
    // MPU6050 sensors
    if (mpu0.valid) {
        doc["a0x"] = serialized(String(mpu0.ax, 2));
        doc["a0y"] = serialized(String(mpu0.ay, 2));
        doc["a0z"] = serialized(String(mpu0.az, 2));
    }
    if (mpu1.valid) {
        doc["a1x"] = serialized(String(mpu1.ax, 2));
        doc["a1y"] = serialized(String(mpu1.ay, 2));
        doc["a1z"] = serialized(String(mpu1.az, 2));
    }
    // Pairing code (temporal, se envía mientras no esté provisionado)
    if (pairingCode.length() > 0) {
        doc["pc"] = pairingCode;
    }

    String json;
    serializeJson(doc, json);

    Serial.printf("[LoRa] TX #%lu — %s\n", (unsigned long)(_fcnt + 1), json.c_str());

    // Transmitir JSON crudo por LoRa (sin encriptar, sin LoRaWAN)
    const uint8_t* src = (const uint8_t*)json.c_str();
    size_t len = json.length();

    // Guardar como hex
    _lastFrameHex = "";
    _lastFrameHex.reserve(len * 2);
    for (size_t i = 0; i < len; i++) {
        char buf[3];
        snprintf(buf, sizeof(buf), "%02X", src[i]);
        _lastFrameHex += buf;
    }

    // RadioLib::transmit espera uint8_t* no-const, copiamos
    uint8_t txBuf[256];
    memcpy(txBuf, src, len);

    int state = _radio.transmit(txBuf, len);
    if (state == RADIOLIB_ERR_NONE) {
        _fcnt++;
        Serial.printf("[LoRa] TX OK  bytes:%d\n", (int)len);
        return true;
    } else {
        Serial.printf("[LoRa] TX ERROR: %d\n", state);
        _lastFrameHex = "";
        return false;
    }
}

String LoRaClient::getDevAddrHex() const {
    char buf[9];
    snprintf(buf, sizeof(buf), "%08X", _devAddr);
    return String(buf);
}

bool LoRaClient::checkProvisioning(uint32_t timeoutMs) {
    String myAddr = "raw-" + getDevAddrHex();

    _radio.startReceive();

    uint32_t start = millis();
    while (millis() - start < timeoutMs) {
        if (digitalRead(LORA_DIO1) == HIGH) {
            String raw;
            int state = _radio.readData(raw);
            if (state == RADIOLIB_ERR_NONE && raw.length() > 0) {
                Serial.printf("[LoRa] RX downlink: %s\n", raw.c_str());
                StaticJsonDocument<256> doc;
                if (!deserializeJson(doc, raw)) {
                    if (doc["prov"] == 1) {
                        const char* d = doc["d"];
                        if (d && String(d) == myAddr) {
                            Serial.println("[LoRa] Prov RX OK — dispositivo provisionado!");
                            return true;
                        }
                    }
                }
            }
        }
        delay(10);
    }

    Serial.println("[LoRa] RX window timeout");
    return false;
}
