#include "gateway_sync.h"
#include "config.h"
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

float readBatteryPct() {
    pinMode(VBAT_ADC_CTRL_PIN, OUTPUT);
    digitalWrite(VBAT_ADC_CTRL_PIN, HIGH);
    delay(10);
    int raw = analogRead(VBAT_ADC_PIN);
    digitalWrite(VBAT_ADC_CTRL_PIN, LOW);
    if (raw < 50) return -1.0f;   // batería no conectada o pin incorrecto
    float v   = (raw / 4095.0f) * 3.3f * 2.0f;   // divisor 1:2
    float pct = (v - 3.0f) / (4.2f - 3.0f) * 100.0f;
    return constrain(pct, 0.0f, 100.0f);
}

bool syncGateway(const String&        serverUrl,
                 const String&        gatewayId,
                 const String&        lorawanPass,
                 const GatewayStatus& st,
                 String&              outName) {
    if (serverUrl.isEmpty()) return false;

    DynamicJsonDocument doc(512);
    doc["gateway_id"] = gatewayId;
    doc["uptime_s"]   = st.uptimeSec;
    doc["pkts_total"] = st.pktsTotal;
    doc["wifi_ssid"]  = st.wifiSsid;
    doc["wifi_rssi"]  = st.wifiRssi;
    if (st.gpsValid) {
        doc["lat"] = st.lat;
        doc["lon"] = st.lon;
    }
    doc["battery_pct"] = (st.batteryPct >= 0.0f) ? st.batteryPct : 0.0f;
    if (st.name.length() > 0)
        doc["name"] = st.name;

    String body;
    serializeJson(doc, body);

    String url = serverUrl + GW_SYNC_ENDPOINT;
    Serial.printf("[GW-SYNC] POST %s\n", url.c_str());

    HTTPClient       http;
    WiFiClientSecure secureClient;
    if (serverUrl.startsWith("https://")) {
        secureClient.setInsecure();
        http.begin(secureClient, url);
    } else {
        http.begin(url);
    }
    http.addHeader("Content-Type", "application/json");
    if (!lorawanPass.isEmpty())
        http.addHeader("Authorization", "Bearer " + lorawanPass);
    http.setTimeout(HTTP_TIMEOUT_MS);

    int code = http.POST(body);
    if (code <= 0) {
        Serial.printf("[GW-SYNC] Error: %s\n", HTTPClient::errorToString(code).c_str());
        http.end();
        return false;
    }

    String resp = http.getString();
    http.end();

    if (code != 200 && code != 201) {
        Serial.printf("[GW-SYNC] HTTP %d: %s\n", code, resp.c_str());
        return false;
    }

    DynamicJsonDocument respDoc(256);
    DeserializationError err = deserializeJson(respDoc, resp);
    if (!err) {
        const char* name = respDoc["name"];
        if (name && strlen(name) > 0)
            outName = String(name);
    }

    Serial.printf("[GW-SYNC] OK — name='%s'\n", outName.c_str());
    return true;
}
