#include "climate_sensor.h"
#include "config.h"
#include <Wire.h>

static bool     _ahtInit = false;
static bool     _ahtSeen = false;
static bool     _ahtPrimed = false;
static float    _lastTemp = NAN;
static float    _lastHum = NAN;
static uint8_t  _ahtAddr = 0x38;

static void initClimateSensor() {
    if (_ahtInit) return;

    pinMode(AHT21B_SDA_PIN, INPUT_PULLUP);
    pinMode(AHT21B_SCL_PIN, INPUT_PULLUP);
    Wire.begin(AHT21B_SDA_PIN, AHT21B_SCL_PIN);
    delay(250);
    Wire.setClock(100000);

    for (uint8_t attempt = 0; attempt < 3 && !_ahtSeen; attempt++) {
        for (uint8_t addr : { (uint8_t)0x38, (uint8_t)0x39 }) {
            Wire.beginTransmission(addr);
            if (Wire.endTransmission() == 0) {
                _ahtAddr = addr;
                _ahtSeen = true;
                break;
            }
        }
        if (!_ahtSeen) delay(100);
    }

    if (_ahtSeen) {
        Wire.beginTransmission(_ahtAddr);
        Wire.write(0xBA);  // soft reset
        Wire.endTransmission();
        delay(80);

        for (uint8_t cmd : { (uint8_t)0xBE, (uint8_t)0xE1 }) {
            Wire.beginTransmission(_ahtAddr);
            Wire.write(cmd);
            Wire.write(0x08);
            Wire.write(0x00);
            Wire.endTransmission();
            delay(40);

            uint8_t status = 0xFF;
            uint8_t n = Wire.requestFrom((int)_ahtAddr, 1);
            if (n == 1) status = Wire.read();
            Serial.printf("[Climate] AHT21B init cmd=0x%02X status=0x%02X\n", cmd, status);
            if (status != 0xFF && (status & 0x08)) break;
        }
    }

    _ahtInit = true;
    Serial.printf("[Climate] AHT21B %s SDA=%d SCL=%d addr=0x%02X\n",
                  _ahtSeen ? "OK" : "NOT FOUND",
                  AHT21B_SDA_PIN, AHT21B_SCL_PIN, _ahtAddr);
}

ClimateReading readClimate() {
    initClimateSensor();
    if (!_ahtSeen) return { NAN, NAN };

    for (uint8_t attempt = 0; attempt < 3; attempt++) {
        Wire.beginTransmission(_ahtAddr);
        Wire.write(0xAC);  // trigger measurement
        Wire.write(0x33);
        Wire.write(0x00);
        bool ok = (Wire.endTransmission() == 0);
        delay(120);

        uint8_t raw[7] = {};
        uint8_t n = Wire.requestFrom((int)_ahtAddr, 7);
        for (uint8_t i = 0; i < n && i < sizeof(raw); i++) {
            raw[i] = Wire.read();
        }
        ok = ok && n >= 6 && !(raw[0] & 0x80);

        uint32_t humRaw = ((uint32_t)raw[1] << 12)
                        | ((uint32_t)raw[2] << 4)
                        | ((uint32_t)raw[3] >> 4);
        uint32_t tempRaw = (((uint32_t)raw[3] & 0x0F) << 16)
                         | ((uint32_t)raw[4] << 8)
                         | raw[5];
        float humPct = (humRaw * 100.0f) / 1048576.0f;
        float tempC = (tempRaw * 200.0f) / 1048576.0f - 50.0f;

        bool valid = ok && !isnan(tempC) && !isnan(humPct)
                  && tempC >= -40.0f && tempC <= 85.0f
                  && humPct >= 0.0f && humPct <= 100.0f;

        if (valid && !_ahtPrimed) {
            _ahtPrimed = true;
            Serial.printf("[Climate] Primera lectura descartada T=%.1fC H=%.0f%%\n", tempC, humPct);
            delay(80);
            continue;
        }

        if (!valid) {
            Serial.printf("[Climate] Invalida raw=%02X %02X %02X %02X %02X %02X %02X\n",
                          raw[0], raw[1], raw[2], raw[3], raw[4], raw[5], raw[6]);
            delay(80);
            continue;
        }

        _lastTemp = tempC;
        _lastHum = humPct;
        Serial.printf("[Climate] T=%.1fC H=%.0f%%\n", tempC, humPct);
        return { tempC, humPct };
    }

    return { _lastTemp, _lastHum };
}
