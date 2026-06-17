#pragma once
#include <Arduino.h>

struct GpsData {
    double   lat    = 0.0;
    double   lon    = 0.0;
    bool     valid  = false;
    uint32_t age_ms = 0;
    uint8_t  fixQuality = 0;    // 0=sin fix, 1=GPS, 2=DGPS, etc. desde GGA
    uint8_t  satellites = 0;    // satélites usados desde GGA
    float    hdop = 0.0f;       // precisión horizontal desde GGA
    float    altitudeM = 0.0f;  // altura MSL desde GGA
    float    speedKmh = 0.0f;   // velocidad desde RMC
    float    courseDeg = 0.0f;  // rumbo desde RMC

    // UTC desde GPRMC (válido cuando timeValid == true)
    bool     timeValid = false;
    uint8_t  utcHour  = 0;
    uint8_t  utcMin   = 0;
    uint8_t  utcSec   = 0;
    uint32_t dateNum  = 0;   // DDMMYY como uint32 — cambia en medianoche UTC
};

class GpsManager {
public:
    GpsManager();
    void    begin();
    void    update();
    void    readFor(uint32_t ms);   // bloquea leyendo UART por ms milisegundos
    GpsData getData()    const;
    bool    hasModule()  const { return _hasData; }  // recibe NMEA aunque no haya fix

private:
    char     _buf[96];
    uint8_t  _idx;
    GpsData  _fix;
    uint32_t _lastFix_ms;
    uint32_t _lastBaudSwitch_ms = 0;
    uint32_t _baud = 0;
    bool     _hasData = false;

    void   _parseLine(const char* line);
    double _nmea2dec(const char* field, char hemi);
    void   _setBaud(uint32_t baud);
};
