#include "display_manager.h"

// TFT_eSPI usa los pines definidos en build_flags (platformio.ini)
// Color scheme
#define COL_BG     TFT_BLACK
#define COL_HDR    TFT_CYAN
#define COL_TEXT   TFT_WHITE
#define COL_DIM    0x7BEF   // gris medio
#define COL_OK     TFT_GREEN
#define COL_WARN   TFT_YELLOW
#define COL_CHG    TFT_YELLOW
#define COL_ERR    TFT_RED

// ── Lightning bolt helpers ──────────────────────────────────
static void drawBatteryBolt(TFT_eSPI& tft, int16_t x, int16_t y, uint16_t color) {
    tft.drawLine(x + 16, y + 1, x + 11, y + 5, color);
    tft.drawLine(x + 11, y + 5, x + 15, y + 5, color);
    tft.drawLine(x + 15, y + 5, x + 10, y + 10, color);
    tft.drawLine(x + 17, y + 1, x + 12, y + 5, color);
    tft.drawLine(x + 12, y + 5, x + 16, y + 5, color);
    tft.drawLine(x + 16, y + 5, x + 11, y + 10, color);
}

static void drawSmallBatteryBolt(TFT_eSPI& tft, int16_t x, int16_t y, uint16_t color) {
    tft.drawLine(x + 6, y + 1, x + 4, y + 3, color);
    tft.drawLine(x + 4, y + 3, x + 6, y + 3, color);
    tft.drawLine(x + 6, y + 3, x + 4, y + 5, color);
}

// ── Constructor ─────────────────────────────────────────────
DisplayManager::DisplayManager()
    : _tft()
    , _lastUpdate(0)
    , _batPct(-1.0f)
    , _batCharging(false)
{}

// ── Init ────────────────────────────────────────────────────
void DisplayManager::begin() {
    pinMode(PIN_TFT_PWR, OUTPUT);
    digitalWrite(PIN_TFT_PWR, HIGH);
    delay(80);

    pinMode(PIN_TFT_BL, OUTPUT);
    digitalWrite(PIN_TFT_BL, PIN_TFT_BL_OFF);

    _tft.init(INITR_GREENTAB);
    _tft.setRotation(1);   // _width=160, _height=128
    _tft.startWrite();
    _tft.writecommand(0x21);  // INVON
    _tft.endWrite();
    _tft.setTextWrap(false);

    delay(50);
    digitalWrite(PIN_TFT_BL, PIN_TFT_BL_ON);

    _tft.fillScreen(COL_BG);
    Serial.println("[Display] init OK (TFT_eSPI ST7735 128x160, visible y=24..103)");
}

// ── Title screen ────────────────────────────────────────────
void DisplayManager::showTitle() {
    _tft.fillScreen(COL_BG);

    _tft.setTextColor(COL_HDR, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 22, VIEW_Y + 8);
    _tft.print("EXALINK LORA GW");

    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 44, VIEW_Y + 36);
    _tft.print("Iniciando...");

    _tft.drawFastHLine(VIEW_X, VIEW_Y + 28, VIEW_W, COL_HDR);
    _clearRightEdge();
}

// ── Status (4 lines) ────────────────────────────────────────
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

// ── LoRa packet screen ──────────────────────────────────────
void DisplayManager::showLoRaPacket(int rssi, float snr,
                                     uint32_t count,
                                     const String& preview) {
    _l1 = "RX LoRa  #" + String(count);
    _l2 = "RSSI: " + String(rssi) + " dBm";
    _l3 = "SNR:  " + String(snr, 1) + " dB";
    _l4 = (preview.length() > 0) ? preview.substring(0, 26) : "";
    _render();
}

// ── Pairing screen ──────────────────────────────────────────
void DisplayManager::showPairing(const String& gwId, const String& code,
                                 uint32_t expiresEpoch) {
    uint32_t now = (uint32_t)time(nullptr);
    if (now < 60) now = (uint32_t)(millis() / 1000);
    int32_t minsLeft = (expiresEpoch > now)
        ? (int32_t)((expiresEpoch - now) / 60)
        : 0;

    _tft.fillScreen(COL_BG);

    // Header
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

    // Label
    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setCursor(VIEW_X + 2, VIEW_Y + 30);
    _tft.print("CODE:");

    // Code in 2 lines, size 2, spaces between digits
    _tft.setTextColor(TFT_WHITE, COL_BG);
    _tft.setTextSize(2);
    String d = code;
    String p1, p2;
    if (d.length() >= 6) {
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

    _l1 = "PAIRING " + String(minsLeft) + "m";
    _l2 = "ID:" + gwId.substring(0, 16);
    _l3 = "CODE: " + p1;
    _l4 = "      " + p2;
    _lastUpdate = millis();
    _clearRightEdge();
}

// ── Paired screen ───────────────────────────────────────────
void DisplayManager::showPaired(const String& gwId, const String& name) {
    _l1 = "REGISTRADO";
    _l2 = "ID:" + gwId.substring(0, 16);
    _l3 = name.length() > 0 ? name.substring(0, 20) : "Gateway OK";
    _l4 = "";
    _render();
}

// ── Set battery state ───────────────────────────────────────
void DisplayManager::setBattery(float pct, bool charging) {
    _batPct = pct;
    _batCharging = charging;
    _render();
}

// ── Header with mini battery widget ─────────────────────────
void DisplayManager::_drawHeader() {
    _tft.setTextColor(COL_HDR, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(VIEW_X + 2, VIEW_Y + 2);
    _tft.print("EXALINK LORA GW");
    _tft.drawFastHLine(VIEW_X, VIEW_Y + 13, VIEW_W, COL_HDR);

    // Mini battery widget (right side of header)
    const int16_t bx = VIEW_X + VIEW_W - 34;  // x=126
    const int16_t by = VIEW_Y + 1;             // y=25
    const uint8_t bat = (_batPct >= 0.0f) ? (uint8_t)_batPct : 0;
    const bool noBattery = (_batPct < 0.0f);

    uint16_t outline = noBattery ? TFT_RED : COL_DIM;
    if (!noBattery) {
        if (_batCharging)           outline = COL_CHG;
        else if (bat > 50)          outline = COL_OK;
        else if (bat > 20)          outline = COL_WARN;
        else                        outline = TFT_RED;
    }

    _tft.drawRect(bx, by, 10, 6, outline);             // 10x6 outline
    _tft.fillRect(bx + 10, by + 1, 2, 4, outline);    // terminal nub 2x4

    // Fill: 8px max inside 1px border
    uint8_t fillW = (uint8_t)(((uint32_t)bat * 8) / 100);
    uint16_t fc;
    if (noBattery)          fc = TFT_RED;
    else if (_batCharging)  fc = COL_CHG;
    else if (bat > 50)      fc = COL_OK;
    else if (bat > 20)      fc = COL_WARN;
    else                    fc = TFT_RED;

    if (fillW > 0)
        _tft.fillRect(bx + 1, by + 1, fillW, 4, fc);
    if (fillW < 8)
        _tft.fillRect(bx + 1 + fillW, by + 1, 8 - fillW, 4, COL_BG);

    if (noBattery) {
        _tft.drawLine(bx + 1, by + 1, bx + 8, by + 4, TFT_RED);
        _tft.drawLine(bx + 8, by + 1, bx + 1, by + 4, TFT_RED);
    } else if (_batCharging) {
        drawSmallBatteryBolt(_tft, bx, by, TFT_BLACK);
        drawSmallBatteryBolt(_tft, bx, by, COL_CHG);
    }

    // Percentage/status text
    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(bx + 14, by);
    char buf[6];
    if (noBattery)              snprintf(buf, sizeof(buf), "--");
    else if (_batCharging)      snprintf(buf, sizeof(buf), "CH");
    else                        snprintf(buf, sizeof(buf), "%u%%", bat);
    _tft.print(buf);
}

// ── Main body battery widget ────────────────────────────────
void DisplayManager::_drawBattery() {
    const int16_t x = VIEW_X + 2;   // x=2
    const int16_t y = VIEW_Y + 68;  // y=92 (bottom area)

    const uint8_t bat = (_batPct >= 0.0f) ? (uint8_t)_batPct : 0;
    const bool noBattery = (_batPct < 0.0f);

    // Color por nivel / estado
    uint16_t fillColor;
    if      (_batCharging)  fillColor = COL_CHG;
    else if (bat > 50)      fillColor = COL_OK;
    else if (bat > 20)      fillColor = COL_WARN;
    else                    fillColor = TFT_RED;

    uint16_t outline = noBattery ? TFT_RED : (_batCharging ? COL_CHG : COL_TEXT);

    // Cuerpo (28x9) + terminal (3x5)
    _tft.drawRect(x, y, 28, 9, outline);
    _tft.fillRect(x + 28, y + 2, 3, 5, outline);

    // Relleno interior (max 24px dentro de borde 2px)
    uint8_t fillW = (uint8_t)(((uint32_t)bat * 24UL) / 100UL);
    if (fillW > 0)
        _tft.fillRect(x + 2, y + 2, fillW, 5, fillColor);
    if (fillW < 24)
        _tft.fillRect(x + 2 + fillW, y + 2, 24 - fillW, 5, COL_BG);

    if (noBattery) {
        _tft.drawLine(x + 3, y + 1, x + 25, y + 7, TFT_RED);
        _tft.drawLine(x + 25, y + 1, x + 3, y + 7, TFT_RED);
    } else if (_batCharging) {
        drawBatteryBolt(_tft, x, y, TFT_BLACK);
        drawBatteryBolt(_tft, x + 1, y, COL_CHG);
    }

    // Text to the right of battery icon
    char buf[40];
    if (noBattery)
        snprintf(buf, sizeof(buf), "S/BAT");
    else if (_batCharging)
        snprintf(buf, sizeof(buf), "%u%% CARGA", bat);
    else
        snprintf(buf, sizeof(buf), "%u%%", bat);

    _tft.setTextColor(COL_DIM, COL_BG);
    _tft.setTextSize(1);
    _tft.setCursor(x + 34, y + 1);
    _tft.print(buf);
}

// ── Clear right edge artifact ───────────────────────────────
void DisplayManager::_clearRightEdge() {
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

// ── Render ──────────────────────────────────────────────────
void DisplayManager::_render() {
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

    _drawBattery();
    _clearRightEdge();
}
