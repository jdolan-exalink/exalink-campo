#include "gps_manager.h"
#include "config.h"
#include <string.h>
#include <stdlib.h>

#define GPS_BAUD   9600

GpsManager::GpsManager() : _idx(0), _lastFix_ms(0) {}

void GpsManager::begin() {
    Serial2.begin(GPS_BAUD, SERIAL_8N1, GNSS_RX_PIN, GNSS_TX_PIN);
    Serial.printf("[GPS] UC6580 UART2 RX=%d TX=%d @ %d baud\n",
                  GNSS_RX_PIN, GNSS_TX_PIN, GPS_BAUD);
}

void GpsManager::update() {
    while (Serial2.available()) {
        char c = (char)Serial2.read();
        if (c == '\n' || c == '\r') {
            if (_idx > 0) {
                _buf[_idx] = '\0';
                _parseLine(_buf);
                _idx = 0;
            }
        } else if (_idx < (uint8_t)(sizeof(_buf) - 1)) {
            _buf[_idx++] = c;
        } else {
            _idx = 0;   // overflow — descartar
        }
    }
    if (_fix.valid)
        _fix.age_ms = millis() - _lastFix_ms;
}

GpsData GpsManager::getData() const { return _fix; }

// Extrae el campo N (base 0) separado por comas, copiando en out[outLen]
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
    // Acepta $GPRMC y $GNRMC
    if (strncmp(line, "$GPRMC,", 7) != 0 &&
        strncmp(line, "$GNRMC,", 7) != 0) return;

    char status[4]  = {};
    char latS[16]   = {};
    char latH[4]    = {};
    char lonS[16]   = {};
    char lonH[4]    = {};

    nmeaField(line, 2, status, sizeof(status));
    if (status[0] != 'A') return;   // sin fix

    nmeaField(line, 3, latS, sizeof(latS));
    nmeaField(line, 4, latH, sizeof(latH));
    nmeaField(line, 5, lonS, sizeof(lonS));
    nmeaField(line, 6, lonH, sizeof(lonH));

    double lat = _nmea2dec(latS, latH[0]);
    double lon = _nmea2dec(lonS, lonH[0]);

    if (lat != 0.0 || lon != 0.0) {
        _fix.lat      = lat;
        _fix.lon      = lon;
        _fix.valid    = true;
        _lastFix_ms   = millis();
        _fix.age_ms   = 0;
        Serial.printf("[GPS] Fix: %.6f, %.6f\n", lat, lon);
    }
}
