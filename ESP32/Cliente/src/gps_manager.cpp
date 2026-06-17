#include "gps_manager.h"
#include "config.h"
#include <string.h>
#include <stdlib.h>

#define GPS_BAUD_PRIMARY    115200UL
#define GPS_BAUD_FALLBACK     9600UL
#define GPS_BAUD_RETRY_MS     3000UL

GpsManager::GpsManager() : _idx(0), _lastFix_ms(0) {}

void GpsManager::_setBaud(uint32_t baud) {
    if (_baud == baud) return;
    Serial2.end();
    delay(50);
    Serial2.begin(baud, SERIAL_8N1, GNSS_RX_PIN, GNSS_TX_PIN);
    _baud = baud;
    _idx = 0;
    _lastBaudSwitch_ms = millis();
    Serial.printf("[GPS] UART2 RX=%d TX=%d @ %lu baud\n",
                  GNSS_RX_PIN, GNSS_TX_PIN, (unsigned long)_baud);
}

void GpsManager::begin() {
    pinMode(GNSS_POWER_PIN, OUTPUT);
    digitalWrite(GNSS_POWER_PIN, HIGH);

    if (GNSS_ENABLE_PIN >= 0) {
        pinMode(GNSS_ENABLE_PIN, OUTPUT);
        digitalWrite(GNSS_ENABLE_PIN, LOW);
    }

    pinMode(GNSS_RESET_PIN, OUTPUT);
    digitalWrite(GNSS_RESET_PIN, HIGH);

    delay(500);

    _setBaud(GPS_BAUD_PRIMARY);
    delay(100);

    while (Serial2.available())
        Serial2.read();

    Serial.printf("[GPS] UC6580 PWR=GPIO%d EN=GPIO%d RST=GPIO%d\n",
                  GNSS_POWER_PIN, GNSS_ENABLE_PIN, GNSS_RESET_PIN);
}

void GpsManager::update() {
    while (Serial2.available()) {
        char c = (char)Serial2.read();
        if (!_hasData)
            Serial.printf("[GPS] raw byte: 0x%02X '%c'\n", (uint8_t)c, (c>=32&&c<127)?c:'.');
        if (c == '\n' || c == '\r') {
            if (_idx > 0) {
                _buf[_idx] = '\0';
                if (_buf[0] == '$') _hasData = true;
                _parseLine(_buf);
                _idx = 0;
            }
        } else if (_idx < (uint8_t)(sizeof(_buf) - 1)) {
            _buf[_idx++] = c;
        } else {
            _idx = 0;
        }
    }
    if (!_hasData && millis() - _lastBaudSwitch_ms >= GPS_BAUD_RETRY_MS) {
        _setBaud(_baud == GPS_BAUD_PRIMARY ? GPS_BAUD_FALLBACK : GPS_BAUD_PRIMARY);
    }
    if (_fix.valid)
        _fix.age_ms = millis() - _lastFix_ms;
}

void GpsManager::readFor(uint32_t ms) {
    uint32_t deadline = millis() + ms;
    while (millis() < deadline) {
        update();
        delay(10);
    }
}

GpsData GpsManager::getData() const { return _fix; }

static bool nmeaField(const char* src, int n, char* out, int outLen) {
    const char* p = src;
    int field = 0;
    while (*p) {
        if (field == n) {
            int i = 0;
            while (*p && *p != ',' && *p != '*' && i < outLen - 1)
                out[i++] = *p++;
            out[i] = '\0';
            return i > 0;
        }
        if (*p == ',') field++;
        p++;
    }
    return false;
}

double GpsManager::_nmea2dec(const char* s, char hemi) {
    if (!s || !*s) return 0.0;
    double raw = atof(s);
    int    deg = (int)(raw / 100);
    double min = raw - (double)deg * 100.0;
    double dec = (double)deg + min / 60.0;
    if (hemi == 'S' || hemi == 'W') dec = -dec;
    return dec;
}

void GpsManager::_parseLine(const char* line) {
    if (strncmp(line, "$GPGGA,", 7) == 0 ||
        strncmp(line, "$GNGGA,", 7) == 0) {
        char fixQ[4] = {};
        char sats[4] = {};
        char hdop[8] = {};
        char alt[12] = {};

        nmeaField(line, 6, fixQ, sizeof(fixQ));
        nmeaField(line, 7, sats, sizeof(sats));
        nmeaField(line, 8, hdop, sizeof(hdop));
        nmeaField(line, 9, alt,  sizeof(alt));

        _fix.fixQuality = (uint8_t)atoi(fixQ);
        _fix.satellites = (uint8_t)atoi(sats);
        _fix.hdop       = (float)atof(hdop);
        _fix.altitudeM  = (float)atof(alt);
        return;
    }

    if (strncmp(line, "$GPRMC,", 7) != 0 &&
        strncmp(line, "$GNRMC,", 7) != 0) return;

    char timeS[12] = {};
    char status[4] = {};
    char latS[16]  = {};
    char latH[4]   = {};
    char lonS[16]  = {};
    char lonH[4]   = {};
    char speedS[12] = {};
    char courseS[12] = {};
    char dateS[8]  = {};

    nmeaField(line, 1, timeS,   sizeof(timeS));
    nmeaField(line, 2, status,  sizeof(status));
    if (status[0] != 'A') return;

    nmeaField(line, 3, latS,  sizeof(latS));
    nmeaField(line, 4, latH,  sizeof(latH));
    nmeaField(line, 5, lonS,  sizeof(lonS));
    nmeaField(line, 6, lonH,  sizeof(lonH));
    nmeaField(line, 7, speedS, sizeof(speedS));
    nmeaField(line, 8, courseS, sizeof(courseS));
    nmeaField(line, 9, dateS, sizeof(dateS));

    if (speedS[0])
        _fix.speedKmh = (float)(atof(speedS) * 1.852);  // knots -> km/h
    if (courseS[0])
        _fix.courseDeg = (float)atof(courseS);

    // Tiempo UTC: "HHMMSS.ss"
    if (timeS[0] && strlen(timeS) >= 6) {
        auto d2 = [](const char* s) -> uint8_t {
            return (uint8_t)((s[0] - '0') * 10 + (s[1] - '0'));
        };
        _fix.utcHour   = d2(timeS);
        _fix.utcMin    = d2(timeS + 2);
        _fix.utcSec    = d2(timeS + 4);
        _fix.timeValid = true;
    }

    // Fecha UTC: "DDMMYY" → número único para detectar cambio de día
    if (dateS[0] && strlen(dateS) >= 6) {
        auto d2 = [](const char* s) -> uint32_t {
            return (uint32_t)((s[0] - '0') * 10 + (s[1] - '0'));
        };
        uint32_t dd = d2(dateS);
        uint32_t mm = d2(dateS + 2);
        uint32_t yy = d2(dateS + 4);
        _fix.dateNum = yy * 10000UL + mm * 100UL + dd;
    }

    double lat = _nmea2dec(latS, latH[0]);
    double lon = _nmea2dec(lonS, lonH[0]);

    if (lat != 0.0 || lon != 0.0) {
        _fix.lat    = lat;
        _fix.lon    = lon;
        _fix.valid  = true;
        _lastFix_ms = millis();
        _fix.age_ms = 0;
        Serial.printf("[GPS] Fix: %.6f, %.6f  UTC %02d:%02d:%02d\n",
                      lat, lon, _fix.utcHour, _fix.utcMin, _fix.utcSec);
    }
}
