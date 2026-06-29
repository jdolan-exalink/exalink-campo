#include "display_manager.h"

// TFT_eSPI usa los pines definidos en build_flags (platformio.ini)
// Color scheme
#define COL_BG     TFT_BLACK
#define COL_HDR    TFT_CYAN
#define COL_TEXT   TFT_WHITE
#define COL_DIM    0x7BEF   // gris medio
#define COL_OK     TFT_GREEN
#define COL_ERR    TFT_RED

DisplayManager::DisplayManager()
    : _tft()
    , _lastUpdate(0)
{}

void DisplayManager::begin() {
    // Power: 80 ms antes de tocar SPI (algunos paneles necesitan > 10 ms)
    pinMode(PIN_TFT_PWR, OUTPUT);
    digitalWrite(PIN_TFT_PWR, HIGH);
    delay(80);

    // Backlight OFF durante init para no mostrar basura
    pinMode(PIN_TFT_BL, OUTPUT);
    digitalWrite(PIN_TFT_BL, PIN_TFT_BL_OFF);

    // Variante estable: controlador 128x160 con vidrio visible 160x80 en y=24..103.
    _tft.init(INITR_GREENTAB);
    _tft.setRotation(1);   // _width=160, _height=128
    _tft.startWrite();
    _tft.writecommand(0x21);  // INVON
    _tft.endWrite();
    _tft.setTextWrap(false);

    // Backlight ON
    delay(50);
    digitalWrite(PIN_TFT_BL, PIN_TFT_BL_ON);

    _tft.fillScreen(COL_BG);
    Serial.println("[Display] init OK (TFT_eSPI ST7735 128x160, visible y=24..103)");
}

void DisplayManager::showTitle() {
    _tft.fillScreen(COL_BG);

    // Título grande centrado
    _tft.setTextColor(COL_HDR, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 22, VIEW_Y + 8);
    _tft.print("EXALINK LORA GW");

    // Subtítulo
    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 44, VIEW_Y + 36);
    _tft.print("Iniciando...");

    _tft.drawFastHLine(VIEW_X, VIEW_Y + 28, VIEW_W, COL_HDR);
    _clearRightEdge();
}

void DisplayManager::showStatus(const String& line1,
                                 const String& line2,
                                 const String& line3,
                                 const String& line4) {
    if (_l1 == line1 && _l2 == line2 && _l3 == line3 && _l4 == line4) {
        return;
    }
    _l1 = line1;
    _l2 = line2;
    _l3 = line3;
    _l4 = line4;
    _render();
}

void DisplayManager::showLoRaPacket(int rssi, float snr,
                                     uint32_t count,
                                     const String& preview) {
    _l1 = "RX LoRa  #" + String(count);
    _l2 = "RSSI: " + String(rssi) + " dBm";
    _l3 = "SNR:  " + String(snr, 1) + " dB";
    _l4 = (preview.length() > 0) ? preview.substring(0, 26) : "";
    _render();
}

void DisplayManager::showPairing(const String& gwId, const String& code,
                                 uint32_t expiresEpoch) {
    uint32_t now = (uint32_t)time(nullptr);
    if (now < 60) now = (uint32_t)(millis() / 1000);
    int32_t minsLeft = (expiresEpoch > now)
        ? (int32_t)((expiresEpoch - now) / 60)
        : 0;

    // Render directo al OLED para evitar throttling y mostrar el codigo
    // de forma destacada (letra grande, fondo).
    _tft.fillScreen(COL_BG);

    // Header amarillo/cyan
    _tft.setTextColor(COL_HDR, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 20, VIEW_Y + 4);
    _tft.print("PAIRING MODE");
    _tft.setCursor(VIEW_X + 110, VIEW_Y + 4);
    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.printf("%dm", minsLeft);
    _tft.drawFastHLine(VIEW_X, VIEW_Y + 14, VIEW_W, COL_HDR);

    // GW ID
    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 2, VIEW_Y + 18);
    _tft.print("ID:");
    _tft.setTextColor(COL_TEXT, COL_BG);
    _tft.print(gwId.substring(0, 16));

    // Label "CODE:"
    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setCursor(VIEW_X + 2, VIEW_Y + 30);
    _tft.print("CODE:");

    // Codigo en 2 lineas, TAMANO 2 (16px de alto), espacios entre digitos
    _tft.setTextColor(TFT_WHITE, COL_BG);
    _tft.setTextSize(2);
    String d = code;
    String p1, p2;
    if (d.length() >= 6) {
        // "123456" -> "1 2 3" / "4 5 6"
        p1 = String(d[0]) + " " + d[1] + " " + d[2];
        p2 = String(d[3]) + " " + d[4] + " " + d[5];
    } else if (d.length() == 3) {
        p1 = String(d[0]) + " " + d[1] + " " + d[2];
    } else {
        p1 = d;
    }
    _tft.setCursor(VIEW_X + 2, VIEW_Y + 38);
    _tft.print(p1);
    if (p2.length() > 0) {
        _tft.setCursor(VIEW_X + 2, VIEW_Y + 56);
        _tft.print(p2);
    }

    // Reset estado para no confundir a showStatus
    _l1 = "PAIRING " + String(minsLeft) + "m";
    _l2 = "ID:" + gwId.substring(0, 16);
    _l3 = "CODE: " + p1;
    _l4 = "      " + p2;
    _lastUpdate = millis();   // evitar que showStatus sobrescriba
    _clearRightEdge();
}

void DisplayManager::showPaired(const String& gwId, const String& name) {
    _l1 = "REGISTRADO";
    _l2 = "ID:" + gwId.substring(0, 16);
    _l3 = name.length() > 0 ? name.substring(0, 20) : "Gateway OK";
    _l4 = "";
    _render();
}

void DisplayManager::_drawHeader() {
    _tft.setTextColor(COL_HDR, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 2, VIEW_Y + 2);
    _tft.print("EXALINK LORA GW");
    _tft.drawFastHLine(VIEW_X, VIEW_Y + 13, VIEW_W, COL_HDR);
}

void DisplayManager::_clearRightEdge() {
    // Stable logical window maps to controller x=2..161, y=25..104.
    // Try clearing the adjacent physical column outside TFT_eSPI clipping.
    _rawFillWindow(162, 25, 162, 104, COL_BG);
}

void DisplayManager::_rawFillWindow(uint16_t xs, uint16_t ys,
                                    uint16_t xe, uint16_t ye,
                                    uint16_t color) {
    const uint32_t pixels = uint32_t(xe - xs + 1) * uint32_t(ye - ys + 1);

    _tft.startWrite();
    _tft.writecommand(0x2A); // CASET
    _tft.writedata(xs >> 8);
    _tft.writedata(xs & 0xFF);
    _tft.writedata(xe >> 8);
    _tft.writedata(xe & 0xFF);

    _tft.writecommand(0x2B); // RASET/PASET
    _tft.writedata(ys >> 8);
    _tft.writedata(ys & 0xFF);
    _tft.writedata(ye >> 8);
    _tft.writedata(ye & 0xFF);

    _tft.writecommand(0x2C); // RAMWR
    _tft.pushBlock(color, pixels);
    _tft.endWrite();
}

void DisplayManager::_render() {
    // Forzar render siempre (era throttled a 100ms, pero impedia que el
    // codigo de pairing apareciera si showStatus se habia llamado recientemente)
    uint32_t now = millis();
    _lastUpdate = now;

    _tft.fillScreen(COL_BG);
    _drawHeader();

    _tft.setTextColor(COL_TEXT, COL_BG);
    _tft.setTextSize(1);

    if (_l1.length()) { _tft.setCursor(VIEW_X + 2, VIEW_Y + 17); _tft.print(_l1); }
    if (_l2.length()) { _tft.setCursor(VIEW_X + 2, VIEW_Y + 29); _tft.print(_l2); }
    if (_l3.length()) { _tft.setCursor(VIEW_X + 2, VIEW_Y + 41); _tft.print(_l3); }
    if (_l4.length()) {
        uint16_t col4 = COL_DIM;
        if      (_l4.startsWith("SRV: OK"))  col4 = COL_OK;
        else if (_l4.startsWith("SRV: ERR")) col4 = COL_ERR;
        _tft.setTextColor(col4, COL_BG);
        _tft.setCursor(VIEW_X + 2, VIEW_Y + 53);
        _tft.print(_l4);
    }
    _clearRightEdge();
}
