#pragma once
#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include "gps_manager.h"

class LoRaClient {
public:
    LoRaClient();
    bool     begin(float freq);
    bool     send(const GpsData& gps, bool gpsModuleSeen, uint8_t battery,
                  float temperatureC, float humidityPct, bool gpsFresh,
                  bool charging, uint32_t bootCount, uint32_t wakeMs);
    uint32_t getTxCount()       const { return _fcnt; }
    uint32_t getDevAddr()       const { return _devAddr; }
    void     setFcnt(uint32_t n)      { _fcnt = n; }
    String   getLastFrameHex()  const { return _lastFrameHex; }
    String   getDevAddrHex()    const;

private:
    SPIClass _spi;
    SX1262   _radio;
    float    _freq;
    uint32_t _devAddr;
    uint32_t _fcnt;
    String   _lastFrameHex;
};
