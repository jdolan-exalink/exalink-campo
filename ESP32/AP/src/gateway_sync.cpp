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

float readBatteryPct() {
    pinMode(VBAT_ADC_CTRL_PIN, OUTPUT);
    digitalWrite(VBAT_ADC_CTRL_PIN, HIGH);
    delay(10);
    int raw = analogRead(VBAT_ADC_PIN);
    digitalWrite(VBAT_ADC_CTRL_PIN, LOW);
    if (raw < 50) return -1.0f;
    float v   = (raw / 4095.0f) * 3.3f * 2.0f;
    float pct = (v - 3.0f) / (4.2f - 3.0f) * 100.0f;
    return constrain(pct, 0.0f, 100.0f);
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
        const char* name = respDoc["name"];
        if (name && strlen(name) > 0)
            result.name = String(name);
        result.isProvisioned = respDoc["is_provisioned"] | false;
        result.isPaired      = respDoc["is_paired"] | false;
    }

    Serial.printf("[GW-SYNC] OK — name='%s' provisioned=%d paired=%d\n",
                  result.name.c_str(), (int)result.isProvisioned, (int)result.isPaired);
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
