#pragma once
#include <Arduino.h>
#include <TFT_eSPI.h>
#include "config.h"

class DisplayManager {
public:
    DisplayManager();
    void begin();
    void turnOn();
    void turnOff();
    bool isOn() const { return _on; }
    void showTitle();
    void showTracker(const String& line1,
                     const String& line2 = "",
                     const String& line3 = "",
                     uint8_t battery = 0,
                     uint32_t dailyCount = 0,
                     uint32_t totalCount = 0,
                     bool charging = false,
                     bool usbConnected = false,
                     float temperature = NAN,
                     float humidity = NAN);

private:
    TFT_eSPI _tft;
    bool     _on;

    String   _l1, _l2, _l3;
    uint8_t  _battery    = 0;
    uint32_t _dailyCount = 0;
    uint32_t _totalCount = 0;
    bool     _charging    = false;
    bool     _usbConnected = false;
    float    _temperature = NAN;
    float    _humidity = NAN;
    uint32_t _lastUpdate;

    static constexpr int16_t VIEW_X = 0;
    static constexpr int16_t VIEW_Y = 24;
    static constexpr int16_t VIEW_W = 160;
    static constexpr int16_t VIEW_H = 80;

    void _render();
    void _drawHeader();
    void _drawBattery();
    void _drawBatteryHeader(int16_t x, int16_t y);
    void _clearRightEdge();
    void _rawFillWindow(uint16_t xs, uint16_t ys,
                        uint16_t xe, uint16_t ye,
                        uint16_t color);
};
