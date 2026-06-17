#include "display_manager.h"

#define COL_BG     TFT_BLACK
#define COL_HDR    TFT_CYAN
#define COL_TEXT   TFT_WHITE
#define COL_DIM    0x7BEF   // gris medio
#define COL_OK     TFT_GREEN
#define COL_WARN   TFT_YELLOW

DisplayManager::DisplayManager()
    : _tft()
    , _on(false)
    , _lastUpdate(0)
{}

void DisplayManager::begin() {
    pinMode(PIN_TFT_PWR, OUTPUT);
    digitalWrite(PIN_TFT_PWR, HIGH);
    delay(80);

    // Backlight OFF por defecto (modo bajo consumo)
    pinMode(PIN_TFT_BL, OUTPUT);
    digitalWrite(PIN_TFT_BL, PIN_TFT_BL_OFF);
    _on = false;

    _tft.init(INITR_GREENTAB);
    _tft.setRotation(1);
    _tft.startWrite();
    _tft.writecommand(0x21);  // INVON
    _tft.endWrite();
    _tft.setTextWrap(false);
    _tft.fillScreen(COL_BG);

    Serial.println("[Display] init OK — backlight OFF (bajo consumo)");
}

void DisplayManager::turnOn() {
    if (_on) return;
    digitalWrite(PIN_TFT_BL, PIN_TFT_BL_ON);
    _on = true;
    _lastUpdate = 0;  // forzar redibujado
}

void DisplayManager::turnOff() {
    if (!_on) return;
    digitalWrite(PIN_TFT_BL, PIN_TFT_BL_OFF);
    _on = false;
}

void DisplayManager::showTitle() {
    _tft.fillScreen(COL_BG);
    _tft.setTextColor(COL_HDR, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 16, VIEW_Y + 8);
    _tft.print("EXALINK TRACKER");
    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setCursor(VIEW_X + 44, VIEW_Y + 36);
    _tft.print("Iniciando...");
    _tft.drawFastHLine(VIEW_X, VIEW_Y + 28, VIEW_W, COL_HDR);
    _clearRightEdge();
}

void DisplayManager::showTracker(const String& line1, const String& line2,
                                  const String& line3, uint8_t battery,
                                  uint32_t dailyCount, uint32_t totalCount,
                                  bool charging, bool usbConnected,
                                  float temperature) {
    if (_l1 == line1 && _l2 == line2 && _l3 == line3
            && _battery == battery && _dailyCount == dailyCount
            && _totalCount == totalCount && _charging == charging
            && _usbConnected == usbConnected
            && ((isnan(_temperature) && isnan(temperature))
                || (!isnan(_temperature) && !isnan(temperature) && _temperature == temperature))) return;
    _l1 = line1; _l2 = line2; _l3 = line3;
    _battery    = battery;
    _dailyCount = dailyCount;
    _totalCount = totalCount;
    _charging   = charging;
    _usbConnected = usbConnected;
    _temperature = temperature;
    if (_on) _render();
}

void DisplayManager::_drawHeader() {
    _tft.setTextColor(COL_HDR, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 2, VIEW_Y + 2);
    _tft.print("EXALINK TRACKER");

    _drawBatteryHeader(126, VIEW_Y + 1);

    _tft.drawFastHLine(VIEW_X, VIEW_Y + 13, VIEW_W, COL_HDR);
}

void DisplayManager::_render() {
    uint32_t now = millis();
    if (now - _lastUpdate < DISPLAY_UPDATE_MS) return;
    _lastUpdate = now;

    _tft.fillScreen(COL_BG);
    _drawHeader();

    _tft.setTextColor(COL_TEXT, COL_BG);
    _tft.setTextSize(1);
    if (_l1.length()) { _tft.setCursor(VIEW_X + 2, VIEW_Y + 17); _tft.print(_l1); }
    if (_l2.length()) { _tft.setCursor(VIEW_X + 2, VIEW_Y + 29); _tft.print(_l2); }

    if (_l3.length()) {
        uint16_t col3;
        if      (_l3.startsWith("Sin modulo")) col3 = TFT_RED;
        else if (_l3.startsWith("Buscando"))   col3 = COL_DIM;
        else                                   col3 = COL_OK;
        _tft.setTextColor(col3, COL_BG);
        _tft.setCursor(VIEW_X + 2, VIEW_Y + 41);
        _tft.print(_l3);
    }
    _drawBattery();

    char tempBuf[12];
    if (isnan(_temperature))
        snprintf(tempBuf, sizeof(tempBuf), "T: N/D");
    else
        snprintf(tempBuf, sizeof(tempBuf), "T: %.1fC", _temperature);
    _tft.setTextColor(COL_TEXT, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 2, VIEW_Y + 67);
    _tft.print(tempBuf);

    _clearRightEdge();
}

void DisplayManager::_drawBattery() {
    const int16_t x = VIEW_X + 2;
    const int16_t y = VIEW_Y + 54;

    // Color según nivel
    uint16_t fillColor;
    if      (_battery > 50) fillColor = COL_OK;
    else if (_battery > 20) fillColor = COL_WARN;
    else                    fillColor = TFT_RED;

    // Cuerpo (28×9) + terminal (3×5)
    _tft.drawRect(x, y, 28, 9, COL_TEXT);
    _tft.fillRect(x + 28, y + 2, 3, 5, COL_TEXT);

    // Relleno interior (máx 24px dentro de borde 2px)
    uint8_t fillW = (uint8_t)(((uint32_t)_battery * 24UL) / 100UL);
    if (fillW > 0)
        _tft.fillRect(x + 2, y + 2, fillW, 5, fillColor);
    if (fillW < 24)
        _tft.fillRect(x + 2 + fillW, y + 2, 24 - fillW, 5, COL_BG);

    // Texto
    char buf[40];
    if (_usbConnected && _battery == 0)
        snprintf(buf, sizeof(buf), "USB sin bat H:%lu T:%lu",
                 (unsigned long)_dailyCount,
                 (unsigned long)_totalCount);
    else if (_battery == 0 && !_charging)
        snprintf(buf, sizeof(buf), "USB  H:%lu T:%lu",
                 (unsigned long)_dailyCount,
                 (unsigned long)_totalCount);
    else if (_charging)
        snprintf(buf, sizeof(buf), "%u%% CHG H:%lu T:%lu",
                 (unsigned)_battery,
                 (unsigned long)_dailyCount,
                 (unsigned long)_totalCount);
    else
        snprintf(buf, sizeof(buf), "%u%%  H:%lu T:%lu",
                 (unsigned)_battery,
                 (unsigned long)_dailyCount,
                 (unsigned long)_totalCount);
    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(x + 34, y + 1);
    _tft.print(buf);
}

void DisplayManager::_drawBatteryHeader(int16_t x, int16_t y) {
    _tft.drawRect(x, y, 10, 6, COL_DIM);
    _tft.fillRect(x + 10, y + 1, 2, 4, COL_DIM);

    uint8_t fillW = (uint8_t)(((uint32_t)_battery * 8) / 100);
    uint16_t fc;
    if (_battery > 50) fc = COL_OK;
    else if (_battery > 20) fc = COL_WARN;
    else fc = TFT_RED;
    if (fillW > 0)
        _tft.fillRect(x + 1, y + 1, fillW, 4, fc);
    if (fillW < 8)
        _tft.fillRect(x + 1 + fillW, y + 1, 8 - fillW, 4, COL_BG);

    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(x + 14, y);
    char buf[6];
    snprintf(buf, sizeof(buf), "%u%%", _battery);
    _tft.print(buf);
}

void DisplayManager::_clearRightEdge() {
    _rawFillWindow(162, 25, 162, 104, COL_BG);
}

void DisplayManager::_rawFillWindow(uint16_t xs, uint16_t ys,
                                     uint16_t xe, uint16_t ye,
                                     uint16_t color) {
    const uint32_t pixels = uint32_t(xe - xs + 1) * uint32_t(ye - ys + 1);
    _tft.startWrite();
    _tft.writecommand(0x2A);
    _tft.writedata(xs >> 8); _tft.writedata(xs & 0xFF);
    _tft.writedata(xe >> 8); _tft.writedata(xe & 0xFF);
    _tft.writecommand(0x2B);
    _tft.writedata(ys >> 8); _tft.writedata(ys & 0xFF);
    _tft.writedata(ye >> 8); _tft.writedata(ye & 0xFF);
    _tft.writecommand(0x2C);
    _tft.pushBlock(color, pixels);
    _tft.endWrite();
}
