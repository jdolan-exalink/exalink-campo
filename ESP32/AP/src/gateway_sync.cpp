#include "gateway_sync.h"
#include "config.h"
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

static void _beginHttp(HTTPClient& http, WiFiClientSecure& secure,
                       const String& url, const String& lorawanPass) {
    if (url.startsWith("https://")) {
        secure.setInsecure();
        http.begin(secure, url);
    } else {
        http.begin(url);
    }
    http.addHeader("Content-Type", "application/json");
    if (!lorawanPass.isEmpty())
        http.addHeader("Authorization", "Bearer " + lorawanPass);
    http.setTimeout(HTTP_TIMEOUT_MS);
}

// ── Battery state (file scope for readBatteryPct + checkCharging) ──
static int     _rawFilt = 0;
static uint8_t _lastPct = 0;

float readBatteryPct() {

    // 1. Activar divisor de voltaje
    pinMode(VBAT_ADC_CTRL_PIN, OUTPUT);
    digitalWrite(VBAT_ADC_CTRL_PIN, HIGH);
    delay(10);

    // 2. Leer raw una vez para estabilizar (discard first conversion)
    (void)analogRead(VBAT_ADC_PIN);
    delay(5);

    // 3. Oversampling: promediar VBAT_SAMPLES lecturas, track min/max
    uint32_t sum = 0;
    int rawMin = 4095, rawMax = 0;
    for (uint8_t i = 0; i < VBAT_SAMPLES; i++) {
        int r = analogRead(VBAT_ADC_PIN);
        sum += r;
        if (r < rawMin) rawMin = r;
        if (r > rawMax) rawMax = r;
        delay(2);
    }
    int raw = (int)(sum / VBAT_SAMPLES);

    // 4. Apagar divisor (ahorrar energía)
    digitalWrite(VBAT_ADC_CTRL_PIN, LOW);

    // 5. Calcular voltaje
    float v = (raw / 4095.0f) * 3.3f * VBAT_DIVIDER;

    Serial.printf("[BAT] raw=%d min=%d max=%d v=%.2f\n", raw, rawMin, rawMax, v);

    // 5b. Validar presencia de batería
    bool present = raw >= 50
                && v >= 2.5f && v <= 4.35f;

    if (!present) {
        Serial.printf("[BAT] NO PRESENT raw=%d v=%.2f\n", raw, v);
        _rawFilt = 0;
        _lastPct = 0;
        return -1.0f;
    }

    // 6. Filtro IIR: 7/8 old + 1/8 new (suavizado)
    if (_rawFilt == 0) _rawFilt = raw;
    else _rawFilt = (_rawFilt * VBAT_FILTER_ALPHA + raw) / (VBAT_FILTER_ALPHA + 1);

    // 7. Convertir a voltaje y porcentaje
    v = (_rawFilt / 4095.0f) * 3.3f * VBAT_DIVIDER;
    float pct = (v - VBAT_VMIN) / (VBAT_VMAX - VBAT_VMIN) * 100.0f;
    uint8_t p = (uint8_t)constrain(pct, 0.0f, 100.0f);

    Serial.printf("[BAT] filt=%d v=%.2f pct=%u\n", _rawFilt, v, p);

    // 8. Histéresis 2% — suprimir fluctuaciones
    if (abs((int)p - (int)_lastPct) <= 2) return _lastPct;
    _lastPct = p;
    return p;
}

bool checkCharging() {
    // Wireless Tracker V1.1: no CHRG_STAT pin exposed.
    // Heuristic: if battery voltage >= 4.15V → likely charging/full.
    // The charger IC (TP4054) holds VBAT near 4.2V when USB connected.
    if (_rawFilt <= 0) return false;
    float v = (_rawFilt / 4095.0f) * 3.3f * VBAT_DIVIDER;
    return v >= 4.15f;
}

GatewaySyncResult syncGateway(const String&        serverUrl,
                               const String&        gatewayId,
                               const String&        lorawanPass,
                               const GatewayStatus& st) {
    GatewaySyncResult result = {false, "", false, false};
    if (serverUrl.isEmpty()) return result;

    DynamicJsonDocument doc(512);
    doc["gateway_id"] = gatewayId;
    doc["uptime_s"]   = st.uptimeSec;
    doc["pkts_total"] = st.pktsTotal;
    doc["wifi_ssid"]  = st.wifiSsid;
    doc["wifi_rssi"]  = st.wifiRssi;
    if (st.gpsValid) { doc["lat"] = st.lat; doc["lon"] = st.lon; }
    doc["battery_pct"] = (st.batteryPct >= 0.0f) ? st.batteryPct : 0.0f;
    doc["charging"]    = st.charging;
    if (st.name.length() > 0) doc["name"] = st.name;

    // Pairing: solo enviamos el código si existe, es válido y no estamos aún registrados.
    if (!st.isPaired && st.pairingCode.length() > 0 && st.pairingExpiresAt > 0) {
        uint32_t now = (uint32_t)time(nullptr);
        if (now < 60) now = (uint32_t)(millis() / 1000);
        if (now < st.pairingExpiresAt) {
            doc["pairing_code"]           = st.pairingCode;
            doc["pairing_expires_at"]     = st.pairingExpiresAt;
            doc["pairing_active"]         = true;
        }
    }
    // NO enviamos is_paired — el backend maneja ese estado via /pair.
    // Si lo enviamos como false, el backend viejo sobreescribe is_paired=1 a 0.

    String body;
    serializeJson(doc, body);

    String url = serverUrl + GW_SYNC_ENDPOINT;
    Serial.printf("[GW-SYNC] POST %s\n", url.c_str());

    HTTPClient       http;
    WiFiClientSecure secure;
    _beginHttp(http, secure, url, lorawanPass);

    int code = http.POST(body);
    if (code <= 0) {
        Serial.printf("[GW-SYNC] Error: %s\n", HTTPClient::errorToString(code).c_str());
        http.end();
        return result;
    }

    String resp = http.getString();
    http.end();

    if (code != 200 && code != 201) {
        Serial.printf("[GW-SYNC] HTTP %d: %s\n", code, resp.c_str());
        return result;
    }

    result.ok = true;

    DynamicJsonDocument respDoc(256);
    if (!deserializeJson(respDoc, resp)) {
        // Si el backend dice que no fue OK, registrar el error
        bool serverOk = respDoc["ok"] | true;
        if (!serverOk) {
            const char* msg = respDoc["msg"] | "";
            Serial.printf("[GW-SYNC] WARN: Backend respondio ok=false: %s\n", msg);
            result.ok = false;
            http.end();
            return result;
        }
        const char* name = respDoc["name"];
        if (name && strlen(name) > 0)
            result.name = String(name);
        result.isProvisioned = respDoc["is_provisioned"] | false;
        result.isPaired      = respDoc["is_paired"] | false;
    } else {
        Serial.printf("[GW-SYNC] WARN: No se pudo parsear respuesta: %s\n", resp.substring(0, 100).c_str());
    }

    Serial.printf("[GW-SYNC] OK — name='%s' provisioned=%d paired=%d\n",
                  result.name.c_str(), (int)result.isProvisioned, (int)result.isPaired);
    Serial.printf("[GW-SYNC] RAW: %s\n", resp.substring(0, 200).c_str());
    return result;
}

bool resetDeviceProvision(const String& serverUrl,
                          const String& provisionCode,
                          const String& deviceUid) {
    if (serverUrl.isEmpty() || provisionCode.isEmpty()) return false;

    String url = serverUrl + PROVISION_ENDPOINT + provisionCode;
    Serial.printf("[Provision] DELETE %s\n", url.c_str());

    DynamicJsonDocument doc(128);
    doc["device_uid"] = deviceUid;
    String body;
    serializeJson(doc, body);

    HTTPClient       http;
    WiFiClientSecure secure;
    if (serverUrl.startsWith("https://")) {
        secure.setInsecure();
        http.begin(secure, url);
    } else {
        http.begin(url);
    }
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(HTTP_TIMEOUT_MS);

    int code = http.sendRequest("DELETE", body);
    http.end();

    if (code == 200 || code == 204) {
        Serial.println("[Provision] Reset OK en servidor.");
        return true;
    }
    Serial.printf("[Provision] Reset HTTP %d — continuando de todas formas.\n", code);
    return false;
}
