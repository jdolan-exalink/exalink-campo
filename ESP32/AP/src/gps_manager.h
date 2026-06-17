#pragma once
#include <Arduino.h>

struct GpsData {
    double   lat    = 0.0;
    double   lon    = 0.0;
    bool     valid  = false;
    uint32_t age_ms = 0;   // ms desde el último fix válido
};

class GpsManager {
public:
    GpsManager();
    void    begin();
    void    update();          // llamar en loop()
    GpsData getData() const;

private:
    char     _buf[96];
    uint8_t  _idx;
    GpsData  _fix;
    uint32_t _lastFix_ms;

    void   _parseLine(const char* line);
    double _nmea2dec(const char* field, char hemi);
};
