#include <Arduino.h>
#include <esp_sleep.h>
#include <driver/rtc_io.h>
#include <driver/gpio.h>
#include <Wire.h>
#include "config.h"
#include "config_manager.h"
#include "lora_client.h"
#include "display_manager.h"
#include "gps_manager.h"
#include "mpu6050_sensor.h"
#include "mp3_player.h"

// ─── RTC persistent state (survives deep sleep) ────────────────────────────────
struct RTCData {
    uint32_t fcnt;          // LoRa frame counter
    uint32_t dailyTxCount;  // TX hoy
    uint32_t lastDateNum;   // fecha GPS del ultimo reset diario
    uint32_t txIntervalMs;  // intervalo entre TX
    uint32_t bootCount;     // cantidad de boots (debug)
    double   lastLat;
    double   lastLon;
    uint32_t lastGpsDateNum;
    uint8_t  lastGpsHour;
    uint8_t  lastGpsMin;
    uint8_t  lastGpsSec;
    bool     lastGpsTimeValid;
    bool     lastGpsKnown;
};
static RTC_DATA_ATTR RTCData _rtc = {};

// ─── LED RGB ──────────────────────────────────────────────────────────────────
static void ledSet(uint8_t r, uint8_t g, uint8_t b) {
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);
#if LED_PIN == GNSS_RESET_PIN
    // En esta placa GPIO35 comparte LED RGB y reset del GNSS. No mandar la
    // señal WS2812 porque contiene pulsos LOW y puede resetear el GPS.
    (void)r; (void)g; (void)b;
    return;
#else
    neopixelWrite(LED_PIN, r, g, b);
    digitalWrite(LED_PIN, HIGH);
#endif
}
static void ledOff() { ledSet(0, 0, 0); }

// ─── Objetos ───────────────────────────────────────────────────────────────────
static LoRaClient      lora;
static DisplayManager  display;
static GpsManager      gps;
static ConfigManager   cfgMgr;
static ClientConfig    cfg;
static uint32_t        _wakeAt;  // cuando despertar del display timeout

// ─── Pairing mode ──────────────────────────────────────────────────────────────
static bool     _pairingMode     = false;
static uint32_t _pairingModeAt   = 0;   // millis cuando entró al modo
static uint32_t _btnLongStart    = 0;
static bool     _btnLongArmed    = false;
static bool     _btnLongFired    = false;

static void enterPairingMode() {
    _pairingMode   = true;
    _pairingModeAt = millis();
    display.turnOn();
    _wakeAt = 0;   // no apagar pantalla mientras está en pairing

    // Generar código random si no hay uno válido
    if (cfg.pairingCode.isEmpty() || !cfgMgr.isPairingCodeValid(cfg)) {
        cfgMgr.startPairing(cfg);
    }

    String uid = ConfigManager::generateDeviceUid();
    display.showTracker(
        "** MODO PAIRING **",
        "Codigo: " + cfg.pairingCode,
        uid.substring(0, 12),
        0, 0, 0, false, Serial.isPlugged()
    );
    Serial.printf("[Pairing] Codigo: %s  UID: %s  expira: %lu\n",
                  cfg.pairingCode.c_str(), uid.c_str(),
                  (unsigned long)cfg.pairingExpiresAt);
}
static bool            _tempSensorInit = false;
static bool            _tempSensorSeen = false;
static bool            _tempSensorPrimed = false;
static float           _lastTemperatureC = NAN;
static float           _lastHumidityPct = NAN;
static uint8_t         _aht21bAddr = 0x38;

struct ClimateReading {
    float temperatureC;
    float humidityPct;
};

// ─── Bateria ───────────────────────────────────────────────────────────────────
static uint8_t readBattery() {
    static int     _rawFilt = 0;
    static uint8_t _lastPct = 0;
    static bool    _lastPresent = false;

    digitalWrite(VBAT_ADC_CTRL_PIN, LOW);
    pinMode(VBAT_ADC_PIN, INPUT_PULLDOWN);
    delay(8);
    int rawOff = analogRead(VBAT_ADC_PIN);

    digitalWrite(VBAT_ADC_CTRL_PIN, HIGH);  // HIGH activa el divisor
    delay(25);
    (void)analogRead(VBAT_ADC_PIN);          // descartar primera conversion tras conmutar

    uint32_t sum = 0;
    int rawMin = 4095;
    int rawMax = 0;
    for (uint8_t i = 0; i < 12; i++) {
        int r = analogRead(VBAT_ADC_PIN);
        sum += r;
        if (r < rawMin) rawMin = r;
        if (r > rawMax) rawMax = r;
        delay(2);
    }
    int raw = (int)(sum / 12);
    digitalWrite(VBAT_ADC_CTRL_PIN, LOW);   // LOW desactiva (ahorro)

    float v = (raw / 4095.0f) * 3.3f * 4.9f;
    bool present = raw >= 450
                && rawMax - rawMin <= 180
                && v >= 2.5f
                && v <= 4.35f;

    if (!present) {
        _rawFilt = 0;
        _lastPct = 0;
        if (_lastPresent) {
            Serial.printf("[Batt] Sin bateria rawOff:%d raw:%d span:%d V:%.2f\n",
                          rawOff, raw, rawMax - rawMin, v);
        }
        _lastPresent = false;
        return 0;
    }

    if (!_lastPresent) {
        Serial.printf("[Batt] Bateria detectada rawOff:%d raw:%d span:%d V:%.2f\n",
                      rawOff, raw, rawMax - rawMin, v);
    }
    _lastPresent = true;

    // IIR low-pass: 87.5% historico, 12.5% nueva lectura
    if (_rawFilt == 0) _rawFilt = raw;
    else _rawFilt = (_rawFilt * 7 + raw) / 8;

    v = (_rawFilt / 4095.0f) * 3.3f * 4.9f;
    float pct = (v - 3.0f) / (4.2f - 3.0f) * 100.0f;
    uint8_t p = (uint8_t)constrain(pct, 0.0f, 100.0f);
    if (abs((int)p - (int)_lastPct) <= 2) return _lastPct;  // histeresis 2%
    _lastPct = p;
    return p;
}

static void initTemperatureSensor() {
    if (_tempSensorInit) return;
    pinMode(AHT21B_SDA_PIN, INPUT_PULLUP);
    pinMode(AHT21B_SCL_PIN, INPUT_PULLUP);
    Wire.begin(AHT21B_SDA_PIN, AHT21B_SCL_PIN);
    delay(250);
    Wire.setClock(100000);

    for (uint8_t attempt = 0; attempt < 3 && !_tempSensorSeen; attempt++) {
        for (uint8_t addr : { (uint8_t)0x38, (uint8_t)0x39 }) {
            Wire.beginTransmission(addr);
            if (Wire.endTransmission() == 0) {
                _aht21bAddr = addr;
                _tempSensorSeen = true;
                break;
            }
        }
        if (!_tempSensorSeen) delay(100);
    }

    if (_tempSensorSeen) {
        Wire.beginTransmission(_aht21bAddr);
        Wire.write(0xBA);  // soft reset
        Wire.endTransmission();
        delay(80);

        for (uint8_t cmd : { (uint8_t)0xBE, (uint8_t)0xE1 }) {
            Wire.beginTransmission(_aht21bAddr);
            Wire.write(cmd);  // init/calibrate: AHT2x first, AHT1x-compatible fallback
            Wire.write(0x08);
            Wire.write(0x00);
            Wire.endTransmission();
            delay(40);

            uint8_t status = 0xFF;
            uint8_t n = Wire.requestFrom((int)_aht21bAddr, 1);
            if (n == 1) status = Wire.read();
            Serial.printf("[Temp] AHT21B init cmd=0x%02X status=0x%02X\n", cmd, status);
            if (status != 0xFF && (status & 0x08)) break;
        }
    }

    _tempSensorInit = true;
    Serial.printf("[Temp] AHT21B %s en SDA=%d SCL=%d addr=0x%02X\n",
                  _tempSensorSeen ? "detectado" : "no detectado",
                  AHT21B_SDA_PIN, AHT21B_SCL_PIN, _aht21bAddr);
}

static ClimateReading readClimate() {
    initTemperatureSensor();
    if (!_tempSensorSeen) return { NAN, NAN };

    for (uint8_t attempt = 0; attempt < 3; attempt++) {
    Wire.beginTransmission(_aht21bAddr);
    Wire.write(0xAC);  // trigger measurement
    Wire.write(0x33);
    Wire.write(0x00);
    bool ok = (Wire.endTransmission() == 0);
    delay(120);

    uint8_t raw[7] = {};
    uint8_t n = Wire.requestFrom((int)_aht21bAddr, 7);
    for (uint8_t i = 0; i < n && i < sizeof(raw); i++) {
        raw[i] = Wire.read();
    }
    ok = ok && n >= 6 && !(raw[0] & 0x80);

    uint32_t humRaw = ((uint32_t)raw[1] << 12)
                    | ((uint32_t)raw[2] << 4)
                    | ((uint32_t)raw[3] >> 4);
    uint32_t tempRaw = (((uint32_t)raw[3] & 0x0F) << 16)
                     | ((uint32_t)raw[4] << 8)
                     | raw[5];
    float humPct = (humRaw * 100.0f) / 1048576.0f;
    float tempC = (tempRaw * 200.0f) / 1048576.0f - 50.0f;

    bool valid = ok && !isnan(tempC) && !isnan(humPct)
              && tempC >= -40.0f && tempC <= 85.0f
              && humPct >= 0.0f && humPct <= 100.0f;

    if (valid && !_tempSensorPrimed) {
        _tempSensorPrimed = true;
        Serial.printf("[Temp] AHT21B primera lectura descartada T=%.2fC H=%.2f%%\n",
                      tempC, humPct);
        delay(80);
        continue;
    }

    if (!valid) {
        Serial.printf("[Temp] Lectura AHT21B invalida ok=%d n=%u raw=%02X %02X %02X %02X %02X %02X %02X T=%.2fC H=%.2f%%\n",
                      ok ? 1 : 0, n,
                      raw[0], raw[1], raw[2], raw[3], raw[4], raw[5], raw[6],
                      tempC, humPct);
        delay(80);
        continue;
    }

    _lastTemperatureC = tempC;
    _lastHumidityPct = humPct;
    Serial.printf("[Temp] AHT21B T=%.2fC H=%.2f%%\n", tempC, humPct);
    return { tempC, humPct };
    }

    return { _lastTemperatureC, _lastHumidityPct };
}

static bool checkCharging() {
    uint8_t lowCount = 0;
    uint8_t highCount = 0;
    for (uint8_t i = 0; i < 5; i++) {
        if (digitalRead(CHRG_STAT_PIN) == LOW) lowCount++;
        else highCount++;
        delayMicroseconds(200);
    }
    bool charging = lowCount >= 3;  // TP4054 STAT LOW = charging

    static int lastRaw = -1;
    static int lastCharging = -1;
    int raw = (lowCount >= highCount) ? LOW : HIGH;
    if (raw != lastRaw || (int)charging != lastCharging) {
        Serial.printf("[Charge] STAT=%s low:%u high:%u charging:%s usb:%s\n",
                      raw == LOW ? "LOW" : "HIGH",
                      lowCount, highCount,
                      charging ? "SI" : "NO",
                      Serial.isPlugged() ? "SI" : "NO");
        lastRaw = raw;
        lastCharging = charging ? 1 : 0;
    }
    return charging;
}

// ─── Reset diario via fecha GPS ───────────────────────────────────────────────
static void checkDayReset(const GpsData& fix) {
    if (!fix.timeValid || fix.dateNum == 0) return;
    if (_rtc.lastDateNum == 0) { _rtc.lastDateNum = fix.dateNum; return; }
    if (fix.dateNum != _rtc.lastDateNum) {
        _rtc.lastDateNum  = fix.dateNum;
        _rtc.dailyTxCount = 0;
        Serial.printf("[Stats] Nuevo dia GPS (%lu)\n", (unsigned long)fix.dateNum);
    }
}

static void rememberLastGps(const GpsData& fix) {
    if (!fix.valid) return;
    _rtc.lastLat = fix.lat;
    _rtc.lastLon = fix.lon;
    _rtc.lastGpsDateNum = fix.dateNum;
    _rtc.lastGpsHour = fix.utcHour;
    _rtc.lastGpsMin = fix.utcMin;
    _rtc.lastGpsSec = fix.utcSec;
    _rtc.lastGpsTimeValid = fix.timeValid;
    _rtc.lastGpsKnown = true;
}

static String formatLastGpsLabel() {
    if (!_rtc.lastGpsKnown) return "Sin fix GPS";
    char buf[32];
    if (_rtc.lastGpsTimeValid && _rtc.lastGpsDateNum != 0) {
        uint32_t mm = (_rtc.lastGpsDateNum / 100UL) % 100;
        uint32_t dd = _rtc.lastGpsDateNum % 100;
        snprintf(buf, sizeof(buf), "Ult GPS %02lu/%02lu %02u:%02u UTC",
                 (unsigned long)dd, (unsigned long)mm,
                 (unsigned)_rtc.lastGpsHour, (unsigned)_rtc.lastGpsMin);
    } else {
        snprintf(buf, sizeof(buf), "Ult GPS sin hora");
    }
    return String(buf);
}

// ─── Pantalla ──────────────────────────────────────────────────────────────────
static void refreshDisplay(const GpsData& fix, uint8_t bat, bool charging, bool usbConnected,
                           ClimateReading climate) {
    if (!display.isOn()) return;
    char l1[28], l2[28], l3[28];
    if (fix.valid) {
        snprintf(l1, sizeof(l1), "%.6f", fix.lat);
        snprintf(l2, sizeof(l2), "%.6f", fix.lon);
        snprintf(l3, sizeof(l3), "GPS %02d:%02d UTC", fix.utcHour, fix.utcMin);
    } else if (_rtc.lastGpsKnown) {
        snprintf(l1, sizeof(l1), "%.6f", _rtc.lastLat);
        snprintf(l2, sizeof(l2), "%.6f", _rtc.lastLon);
        auto gpsLabel = formatLastGpsLabel();
        snprintf(l3, sizeof(l3), "%s", gpsLabel.c_str());
    } else {
        snprintf(l1, sizeof(l1), "%s", lora.getDevAddrHex().c_str());
        snprintf(l2, sizeof(l2), "TX c/%lus", (unsigned long)(_rtc.txIntervalMs / 1000));
        snprintf(l3, sizeof(l3), "DeepSleep #%lu", (unsigned long)_rtc.bootCount);
    }
    display.showTracker(l1, l2, l3, bat, _rtc.dailyTxCount, _rtc.fcnt, charging, usbConnected,
                        climate.temperatureC, climate.humidityPct);
}

// ─── GPS power: mantener HIGH durante sleep para hot fix ──────────────────────
static void gpsPowerOn() {
    rtc_gpio_hold_dis((gpio_num_t)GNSS_POWER_PIN);
    rtc_gpio_deinit((gpio_num_t)GNSS_POWER_PIN);  // volver a GPIO normal
    pinMode(GNSS_POWER_PIN, OUTPUT);
    digitalWrite(GNSS_POWER_PIN, HIGH);
}

static void gpsHoldForSleep() {
    rtc_gpio_init((gpio_num_t)GNSS_POWER_PIN);
    rtc_gpio_set_direction((gpio_num_t)GNSS_POWER_PIN, RTC_GPIO_MODE_OUTPUT_ONLY);
    rtc_gpio_set_level((gpio_num_t)GNSS_POWER_PIN, 1);   // HIGH = GPS ON para hot fix
    rtc_gpio_hold_en((gpio_num_t)GNSS_POWER_PIN);
}

// ─── Ciclo de TX ──────────────────────────────────────────────────────────────
static void doTx() {
    ledSet(0, 180, 0);
    uint32_t ledOnMs = millis();

    gps.readFor(GPS_WINDOW_MS);
    GpsData fix = gps.getData();
    bool gpsFresh = fix.valid;
    GpsData txFix = fix;
    if (!gpsFresh && _rtc.lastGpsKnown) {
        txFix.lat = _rtc.lastLat;
        txFix.lon = _rtc.lastLon;
        txFix.valid = true;
        txFix.timeValid = _rtc.lastGpsTimeValid;
        txFix.utcHour = _rtc.lastGpsHour;
        txFix.utcMin = _rtc.lastGpsMin;
        txFix.utcSec = _rtc.lastGpsSec;
        txFix.dateNum = _rtc.lastGpsDateNum;
    }
    uint8_t bat = readBattery();
    ClimateReading climate = readClimate();
    MpuReading mpu0 = readMpu6050(0);
    MpuReading mpu1 = readMpu6050(1);

    // Ahorro extremo: si bateria <= 10% → TX cada 1h
    if (bat <= LOW_BAT_THRESHOLD && _rtc.txIntervalMs != LOW_BAT_INTERVAL_MS) {
        _rtc.txIntervalMs = LOW_BAT_INTERVAL_MS;
        Serial.printf("[Batt] CRITICA %d%% <= %d%% → TX cada 1h\n", bat, LOW_BAT_THRESHOLD);
    } else if (bat > LOW_BAT_RESTORE && _rtc.txIntervalMs == LOW_BAT_INTERVAL_MS) {
        _rtc.txIntervalMs = cfg.refreshFreqS * 1000UL;
        Serial.printf("[Batt] Recuperada %d%% > %d%% → TX normal\n", bat, LOW_BAT_RESTORE);
    }
    char tempBuf[16];
    if (isnan(climate.temperatureC)) snprintf(tempBuf, sizeof(tempBuf), "N/D");
    else snprintf(tempBuf, sizeof(tempBuf), "%.1fC", climate.temperatureC);

    checkDayReset(fix);
    rememberLastGps(fix);

    // Enviar código de pairing si no está provisionado
    String pairingCode = "";
    if (!cfg.isProvisioned && !cfg.pairingCode.isEmpty() && cfgMgr.isPairingCodeValid(cfg)) {
        pairingCode = cfg.pairingCode;
    }
    lora.send(txFix, gps.hasModule(), bat, climate.temperatureC, climate.humidityPct, gpsFresh,
              checkCharging(), _rtc.bootCount, millis(), mpu0, mpu1, pairingCode);
    _rtc.fcnt = lora.getTxCount();
    _rtc.dailyTxCount++;

    Serial.printf("[Main] TX #%lu (hoy:%lu) GPS:%s bat:%d%% temp:%s deepBoots:%lu\n",
                  (unsigned long)_rtc.fcnt,
                  (unsigned long)_rtc.dailyTxCount,
                  fix.valid ? "OK" : "no", (int)bat, tempBuf,
                  (unsigned long)_rtc.bootCount);

    refreshDisplay(txFix, bat, checkCharging(), Serial.isPlugged(), climate);

#if LED_PIN != GNSS_RESET_PIN
    uint32_t elapsed = millis() - ledOnMs;
    if (elapsed < LED_TX_MS) delay(LED_TX_MS - elapsed);
#endif
    ledOff();
}

// ─── Boton (wake del deep sleep) ──────────────────────────────────────────────
static void onButtonWake() {
    delay(50);
    while (digitalRead(BTN_PIN) == LOW) delay(10);
    delay(30);

    display.turnOn();
    _wakeAt = millis() + DISPLAY_ON_MS;

    GpsData fix = gps.getData();
    if (!fix.valid && _rtc.lastGpsKnown) {
        fix.lat = _rtc.lastLat;
        fix.lon = _rtc.lastLon;
        fix.valid = true;
        fix.timeValid = _rtc.lastGpsTimeValid;
        fix.utcHour = _rtc.lastGpsHour;
        fix.utcMin = _rtc.lastGpsMin;
        fix.utcSec = _rtc.lastGpsSec;
        fix.dateNum = _rtc.lastGpsDateNum;
    }
    refreshDisplay(fix, readBattery(), checkCharging(), Serial.isPlugged(),
                   { _lastTemperatureC, _lastHumidityPct });
}

// ─── Deep sleep ────────────────────────────────────────────────────────────────
static void enterDeepSleep(uint32_t sleepMs) {
    if (sleepMs < 1000) sleepMs = 1000;

    // Mantener GPS encendido durante sleep para hot fix
    gpsHoldForSleep();

    // Configurar wake sources
    esp_sleep_enable_timer_wakeup((uint64_t)sleepMs * 1000ULL);
    esp_sleep_enable_ext0_wakeup((gpio_num_t)BTN_PIN, 0);  // GPIO0 LOW = boton presionado

    Serial.printf("[DeepSleep] %lu s  fcnt=%lu  daily=%lu\n",
                  (unsigned long)(sleepMs / 1000),
                  (unsigned long)_rtc.fcnt,
                  (unsigned long)_rtc.dailyTxCount);
    Serial.flush();
    delay(50);

    esp_deep_sleep_start();
}

// ─── setup() ──────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(SERIAL_BAUD);

    // Liberar GPIO hold del GPS (viene de deep sleep)
    rtc_gpio_hold_dis((gpio_num_t)GNSS_POWER_PIN);

    // Primer boot: inicializar RTC
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    if (cause != ESP_SLEEP_WAKEUP_TIMER && cause != ESP_SLEEP_WAKEUP_GPIO) {
        _rtc.fcnt         = 0;
        _rtc.dailyTxCount = 0;
        _rtc.lastDateNum  = 0;
        _rtc.txIntervalMs = TX_INTERVAL_MS;
        _rtc.bootCount    = 0;
        _rtc.lastLat = 0.0;
        _rtc.lastLon = 0.0;
        _rtc.lastGpsDateNum = 0;
        _rtc.lastGpsHour = 0;
        _rtc.lastGpsMin = 0;
        _rtc.lastGpsSec = 0;
        _rtc.lastGpsTimeValid = false;
        _rtc.lastGpsKnown = false;
        Serial.println("\n=======================================");
        Serial.println("   EXALINK LORA TRACKER v1.1 — DeepSleep");
        Serial.println("=======================================");
    } else {
        delay(50);
        Serial.printf("\n[Wake] cause=%d  boot#%lu  fcnt=%lu\n",
                      (int)cause, (unsigned long)_rtc.bootCount, (unsigned long)_rtc.fcnt);
    }
    _rtc.bootCount++;

    pinMode(BTN_PIN, INPUT_PULLUP);
    ledOff();

    // Inicializar pin de control del divisor de bateria
    pinMode(VBAT_ADC_CTRL_PIN, OUTPUT);
    digitalWrite(VBAT_ADC_CTRL_PIN, LOW);
    pinMode(VBAT_ADC_PIN, INPUT_PULLDOWN);
    analogReadResolution(12);
    analogSetPinAttenuation(VBAT_ADC_PIN, ADC_11db);

    // Pin de estado de carga TP4054
    pinMode(CHRG_STAT_PIN, INPUT_PULLUP);

    // GPS: prender y mantener HIGH (ya liberamos hold arriba)
    gpsPowerOn();

    // Display: encender en primer boot (cold), al despertar por boton o con USB
    display.begin();
    bool isColdBoot = (cause != ESP_SLEEP_WAKEUP_TIMER && cause != ESP_SLEEP_WAKEUP_GPIO);
    if (Serial.isPlugged() || cause == ESP_SLEEP_WAKEUP_GPIO || isColdBoot) {
        display.turnOn();
        if (!Serial.isPlugged())
            _wakeAt = millis() + DISPLAY_ON_MS;
    } else {
        display.turnOff();
    }

    // Config NVS
    cfgMgr.begin();
    cfgMgr.load(cfg);
    if (_rtc.bootCount == 1)
        _rtc.txIntervalMs = cfg.refreshFreqS * 1000UL;

    // Entrar en modo pairing si no está provisionado (pero seguir con LoRa)
    if (!cfg.isProvisioned && isColdBoot) {
        enterPairingMode();
        // No return — seguir inicializando LoRa para enviar el código
    }

    // GPS UART
    gps.begin();
    initTemperatureSensor();
    initMpu6050();

    // LoRa
    if (!lora.begin(LORA_FREQ_DEFAULT)) {
        Serial.println("[ERROR] LoRa fail");
        display.turnOn();
        display.showTracker("ERROR: LoRa fail", "Verificar hardware");
        while (true) delay(5000);
    }
    lora.setFcnt(_rtc.fcnt);  // restaurar frame counter
    Serial.printf("[Main] DevAddr: %s\n", lora.getDevAddrHex().c_str());

    // Mostrar tracker inicial tras el titulo (evita que pantalla quede en "Iniciando...")
    if (display.isOn()) {
        char buf[28];
        snprintf(buf, sizeof(buf), "TX c/%lus", (unsigned long)(_rtc.txIntervalMs / 1000));
        ClimateReading climate = readClimate();
        display.showTracker(lora.getDevAddrHex().c_str(), buf, "Buscando GPS...",
                            readBattery(), 0, _rtc.fcnt, checkCharging(), Serial.isPlugged(),
                            climate.temperatureC, climate.humidityPct);
    }

    // Si el usuario presiono el boton, mostrar pantalla
    if (cause == ESP_SLEEP_WAKEUP_GPIO) {
        onButtonWake();
    }
}

// ─── loop() ───────────────────────────────────────────────────────────────────
void loop() {
    uint32_t now = millis();

    // ── Modo pairing: seguir haciendo TX con el código, display muestra pairing ─
    if (_pairingMode) {
        bool pressed = (digitalRead(BTN_PIN) == LOW);
        if (pressed) {
            enterPairingMode();
            delay(300);
        }
        // Auto-regenerar código cuando está por expirar (< 1 min)
        if (!cfgMgr.isPairingCodeValid(cfg)) {
            cfgMgr.startPairing(cfg);
            enterPairingMode();
        }
        // Mantener pantalla encendida
        if (!display.isOn()) display.turnOn();

        // TX periódico con el código de pairing (10s en modo pairing)
        static uint32_t lastPairingTxMs = 0;
        if (now - lastPairingTxMs >= 10000) {
            doTx();
            lastPairingTxMs = millis();
        }
        delay(100);
        return;
    }

    // ── Botón: corto → pantalla / largo 10s → pairing mode ───────────────────
    bool btnNow = (digitalRead(BTN_PIN) == LOW);
    if (btnNow && !_btnLongArmed) {
        _btnLongStart = now;
        _btnLongArmed = true;
        _btnLongFired = false;
    } else if (btnNow && _btnLongArmed && !_btnLongFired) {
        if (now - _btnLongStart >= BTN_LONG_PRESS_MS) {
            _btnLongFired = true;
            Serial.println("[BTN] 10s — reset a modo pairing.");
            display.showTracker("Reseteando...", "Modo pairing", "", 0, 0, 0, false, Serial.isPlugged());
            delay(1000);
            cfgMgr.resetProvision();
            _pairingMode = false;   // enterPairingMode() lo setea
            enterPairingMode();
        }
    } else if (!btnNow) {
        if (_btnLongArmed && !_btnLongFired && now - _btnLongStart < BTN_LONG_PRESS_MS) {
            // Pulsación corta: encender pantalla
            if (!display.isOn()) onButtonWake();
        }
        _btnLongArmed = false;
        _btnLongFired = false;
    }

    // Detectar transiciones USB
    static bool _lastUsbPlugged = false;
    bool usbPlugged = Serial.isPlugged();
    if (usbPlugged && !_lastUsbPlugged) {
        if (!display.isOn()) { display.turnOn(); _wakeAt = 0; }
    } else if (!usbPlugged && _lastUsbPlugged && display.isOn()) {
        _wakeAt = now + DISPLAY_ON_MS;
    }
    _lastUsbPlugged = usbPlugged;

    gps.update();

    // TX periodico
    static uint32_t lastTxMs = 0;
    if (lastTxMs == 0) lastTxMs = now - _rtc.txIntervalMs;
    if (now - lastTxMs >= _rtc.txIntervalMs) {
        doTx();
        lastTxMs = millis();
        now = lastTxMs;
        if (display.isOn() && !Serial.isPlugged())
            _wakeAt = now + DISPLAY_ON_MS;
    }

    // USB: pantalla siempre
    if (Serial.isPlugged()) {
        static uint32_t lastUsbClimateMs = 0;
        static bool usbClimateRead = false;
        if (!display.isOn()) { display.turnOn(); _wakeAt = 0; }
        if (!usbClimateRead || now - lastUsbClimateMs >= 60000UL) {
            readClimate();
            lastUsbClimateMs = now;
            usbClimateRead = true;
        }
        GpsData liveFix = gps.getData();
        if (!liveFix.valid && _rtc.lastGpsKnown) {
            liveFix.lat = _rtc.lastLat;
            liveFix.lon = _rtc.lastLon;
            liveFix.valid = true;
            liveFix.timeValid = _rtc.lastGpsTimeValid;
            liveFix.utcHour = _rtc.lastGpsHour;
            liveFix.utcMin = _rtc.lastGpsMin;
            liveFix.utcSec = _rtc.lastGpsSec;
            liveFix.dateNum = _rtc.lastGpsDateNum;
        }
        refreshDisplay(liveFix, readBattery(), checkCharging(), true,
                       { _lastTemperatureC, _lastHumidityPct });
    }

    // Apagar pantalla por timeout
    if (display.isOn() && _wakeAt > 0 && millis() >= _wakeAt && !Serial.isPlugged()) {
        display.turnOff();
        _wakeAt = 0;
    }

    // Calcular cuanto dormir
    uint32_t nextTxMs = lastTxMs + _rtc.txIntervalMs;
    uint32_t sleepMs  = 0;
    if (nextTxMs > now)
        sleepMs = nextTxMs - now;

    // Si hay display encendido, limitar el sleep
    if (display.isOn() && _wakeAt > 0) {
        uint32_t displayMs = (_wakeAt > now) ? _wakeAt - now : 0;
        if (sleepMs == 0 || displayMs < sleepMs)
            sleepMs = displayMs;
    }

    // Garantizar MIN_WAKE_MS despierto
    if (now < MIN_WAKE_MS) {
        uint32_t minRemain = MIN_WAKE_MS - now;
        if (sleepMs == 0 || minRemain > sleepMs)
            sleepMs = minRemain;
    }

    if (sleepMs > 500 && !Serial.isPlugged() && !display.isOn()) {
        enterDeepSleep(sleepMs);
        // Nunca llega aca — deep sleep reinicia
    }

    delay(20);
}
