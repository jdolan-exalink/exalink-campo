#pragma once
#include <Arduino.h>
#include <TFT_eSPI.h>
#include "config.h"

class DisplayManager {
public:
    DisplayManager();
    void begin();
    void showTitle();
    void showStatus(const String& line1,
                    const String& line2 = "",
                    const String& line3 = "",
                    const String& line4 = "");
    void showLoRaPacket(int rssi, float snr, uint32_t count,
                        const String& preview = "");

private:
    TFT_eSPI _tft;

    String   _l1, _l2, _l3, _l4;
    uint32_t _lastUpdate;

    static constexpr int16_t VIEW_X = 0;
    static constexpr int16_t VIEW_Y = 24;
    static constexpr int16_t VIEW_W = 160;
    static constexpr int16_t VIEW_H = 80;

    void _render();
    void _drawHeader();
    void _clearRightEdge();
    void _rawFillWindow(uint16_t xs, uint16_t ys,
                        uint16_t xe, uint16_t ye,
                        uint16_t color);
};
