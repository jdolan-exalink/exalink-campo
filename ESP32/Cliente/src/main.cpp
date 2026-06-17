#include <Arduino.h>
#include <esp_sleep.h>
#include <driver/rtc_io.h>
#include <driver/gpio.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "config.h"
#include "config_manager.h"
#include "lora_client.h"
#include "display_manager.h"
#include "gps_manager.h"

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
static OneWire         _oneWire(DS18B20_DATA_PIN);
static DallasTemperature _ds18b20(&_oneWire);
static bool            _tempSensorInit = false;
static bool            _tempSensorSeen = false;
static float           _lastTemperatureC = NAN;

// ─── Bateria ───────────────────────────────────────────────────────────────────
static uint8_t readBattery() {
    static int    _rawFilt = 0;
    static uint8_t _lastPct = 0;

    digitalWrite(VBAT_ADC_CTRL_PIN, HIGH);  // HIGH activa el divisor
    delay(2);
    int raw = analogRead(VBAT_ADC_PIN);
    digitalWrite(VBAT_ADC_CTRL_PIN, LOW);   // LOW desactiva (ahorro)

    // IIR low-pass: 87.5% historico, 12.5% nueva lectura
    if (_rawFilt == 0) _rawFilt = raw;
    else _rawFilt = (_rawFilt * 7 + raw) / 8;

    if (_rawFilt < 300) { _rawFilt = 0; _lastPct = 0; return 0; }  // sin bateria

    float v   = (_rawFilt / 4095.0f) * 3.3f * 4.9f;
    float pct = (v - 3.0f) / (4.2f - 3.0f) * 100.0f;
    uint8_t p = (uint8_t)constrain(pct, 0.0f, 100.0f);
    if (abs((int)p - (int)_lastPct) <= 2) return _lastPct;  // histeresis 2%
    _lastPct = p;
    return p;
}

static void initTemperatureSensor() {
    if (_tempSensorInit) return;
    pinMode(DS18B20_DATA_PIN, INPUT_PULLUP);
    _ds18b20.begin();
    _ds18b20.setWaitForConversion(true);
    _ds18b20.setResolution(11);
    _tempSensorSeen = _ds18b20.getDeviceCount() > 0;
    _tempSensorInit = true;
    Serial.printf("[Temp] DS18B20 %s en GPIO%d\n",
                  _tempSensorSeen ? "detectado" : "no detectado",
                  DS18B20_DATA_PIN);
}

static float readTemperatureC() {
    initTemperatureSensor();
    if (!_tempSensorSeen) return NAN;

    _ds18b20.requestTemperatures();
    float tempC = _ds18b20.getTempCByIndex(0);
    if (tempC == DEVICE_DISCONNECTED_C || tempC == 85.0f || tempC < -55.0f || tempC > 125.0f) {
        return _lastTemperatureC;
    }

    _lastTemperatureC = tempC;
    return tempC;
}

static bool checkCharging() {
    return (digitalRead(CHRG_STAT_PIN) == LOW);  // TP4054 STAT LOW = charging
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
static void refreshDisplay(const GpsData& fix, uint8_t bat, bool charging, bool usbConnected, float tempC) {
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
    display.showTracker(l1, l2, l3, bat, _rtc.dailyTxCount, _rtc.fcnt, charging, usbConnected, tempC);
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
    float tempC = readTemperatureC();

    // Ahorro extremo: si bateria <= 10% → TX cada 1h
    if (bat <= LOW_BAT_THRESHOLD && _rtc.txIntervalMs != LOW_BAT_INTERVAL_MS) {
        _rtc.txIntervalMs = LOW_BAT_INTERVAL_MS;
        Serial.printf("[Batt] CRITICA %d%% <= %d%% → TX cada 1h\n", bat, LOW_BAT_THRESHOLD);
    } else if (bat > LOW_BAT_RESTORE && _rtc.txIntervalMs == LOW_BAT_INTERVAL_MS) {
        _rtc.txIntervalMs = cfg.refreshFreqS * 1000UL;
        Serial.printf("[Batt] Recuperada %d%% > %d%% → TX normal\n", bat, LOW_BAT_RESTORE);
    }
    char tempBuf[16];
    if (isnan(tempC)) snprintf(tempBuf, sizeof(tempBuf), "N/D");
    else snprintf(tempBuf, sizeof(tempBuf), "%.1fC", tempC);

    checkDayReset(fix);
    rememberLastGps(fix);

    lora.send(txFix, gps.hasModule(), bat, tempC, gpsFresh,
              checkCharging(), _rtc.bootCount, millis());
    _rtc.fcnt = lora.getTxCount();
    _rtc.dailyTxCount++;

    Serial.printf("[Main] TX #%lu (hoy:%lu) GPS:%s bat:%d%% temp:%s deepBoots:%lu\n",
                  (unsigned long)_rtc.fcnt,
                  (unsigned long)_rtc.dailyTxCount,
                  fix.valid ? "OK" : "no", (int)bat, tempBuf,
                  (unsigned long)_rtc.bootCount);

    refreshDisplay(txFix, bat, checkCharging(), Serial.isPlugged(), tempC);

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
    refreshDisplay(fix, readBattery(), checkCharging(), Serial.isPlugged(), _lastTemperatureC);
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
    digitalWrite(VBAT_ADC_CTRL_PIN, HIGH);

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

    // GPS UART
    gps.begin();
    initTemperatureSensor();

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
        display.showTracker(lora.getDevAddrHex().c_str(), buf, "Buscando GPS...",
                            readBattery(), 0, _rtc.fcnt, checkCharging(), Serial.isPlugged(),
                            readTemperatureC());
    }

    // Si el usuario presiono el boton, mostrar pantalla
    if (cause == ESP_SLEEP_WAKEUP_GPIO) {
        onButtonWake();
    }
}

// ─── loop() ───────────────────────────────────────────────────────────────────
void loop() {
    uint32_t now = millis();

    // Detectar transiciones USB
    static bool _lastUsbPlugged = false;
    bool usbPlugged = Serial.isPlugged();
    if (usbPlugged && !_lastUsbPlugged) {
        if (!display.isOn()) { display.turnOn(); _wakeAt = 0; }
    } else if (!usbPlugged && _lastUsbPlugged && display.isOn()) {
        _wakeAt = now + DISPLAY_ON_MS;
    }
    _lastUsbPlugged = usbPlugged;

    // Boton durante ejecucion
    if (digitalRead(BTN_PIN) == LOW) {
        if (!display.isOn()) onButtonWake();
        now = millis();
    }

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
        if (!display.isOn()) { display.turnOn(); _wakeAt = 0; }
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
        refreshDisplay(liveFix, readBattery(), checkCharging(), true, _lastTemperatureC);
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
