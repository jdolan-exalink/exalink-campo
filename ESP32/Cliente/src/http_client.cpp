#include "http_client.h"
#include "config.h"
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

// ─── helper: HTTPS POST/GET con cert insegura ─────────────────────────────────
static HTTPClient* _beginRequest(WiFiClientSecure& sc,
                                  const String& url) {
    sc.setInsecure();
    auto* h = new HTTPClient();
    h->begin(sc, url);
    h->addHeader("Content-Type", "application/json");
    h->addHeader("Authorization", "Bearer " SERVER_LORAWAN_PASS);
    h->setTimeout(HTTP_TIMEOUT_MS);
    return h;
}

// ─── GET /api/lora/device/config ──────────────────────────────────────────────
bool getDeviceConfig(const String& serverUrl,
                     const String& devAddrHex,
                     uint32_t&     outRefreshS,
                     String&       outName,
                     String&       outDevType) {
    String url = serverUrl + API_CONFIG_ENDPOINT +
                 "?dev_addr=raw-" + devAddrHex;
    Serial.printf("[HTTP] GET %s\n", url.c_str());

    WiFiClientSecure sc;
    HTTPClient* h = _beginRequest(sc, url);

    int code = h->GET();
    if (code <= 0) {
        Serial.printf("[HTTP] Config GET error: %s\n",
                      HTTPClient::errorToString(code).c_str());
        delete h; return false;
    }

    String body = h->getString();
    delete h;

    if (code != 200) {
        Serial.printf("[HTTP] Config HTTP %d: %s\n", code, body.c_str());
        return false;
    }

    DynamicJsonDocument doc(256);
    if (deserializeJson(doc, body)) return false;

    JsonObject cfg = doc["config"];
    if (cfg.isNull()) return false;

    if (cfg.containsKey("refresh_freq_s"))
        outRefreshS = cfg["refresh_freq_s"].as<uint32_t>();
    if (cfg.containsKey("name"))
        outName = cfg["name"].as<String>();
    if (cfg.containsKey("device_type"))
        outDevType = cfg["device_type"].as<String>();

    Serial.printf("[HTTP] Config OK — refresh:%lus name:'%s' type:'%s'\n",
                  (unsigned long)outRefreshS,
                  outName.c_str(), outDevType.c_str());
    return true;
}

// ─── POST /api/lora/equipment ─────────────────────────────────────────────────
bool postEquipment(const String& serverUrl,
                   const String& devAddrHex,
                   const String& name,
                   const String& devType,
                   double lat, double lon, bool gpsValid,
                   const String& wifiSsid, int wifiRssi,
                   float battery,
                   float temperature,
                   uint32_t& outRefreshS,
                   String&   outName) {
    DynamicJsonDocument doc(512);
    doc["dev_addr"]    = "raw-" + devAddrHex;
    doc["name"]        = name.length() ? name : devAddrHex;
    doc["device_type"] = devType;
    doc["hw_version"]  = HW_VERSION_DEFAULT;
    doc["wifi_ssid"]   = wifiSsid;
    doc["wifi_rssi"]   = wifiRssi;
    doc["battery_pct"] = battery;   // float: 85.3
    if (!isnan(temperature)) {
        doc["temperature"] = temperature;
    } else {
        doc["temperature"] = nullptr;
    }
    if (gpsValid) {
        doc["lat"] = lat;
        doc["lon"] = lon;
    } else {
        doc["lat"] = nullptr;
        doc["lon"] = nullptr;
    }

    String body;
    serializeJson(doc, body);

    String url = serverUrl + API_EQUIPMENT_ENDPOINT;
    Serial.printf("[HTTP] POST equipment: %s\n", body.c_str());

    WiFiClientSecure sc;
    HTTPClient* h = _beginRequest(sc, url);
    int code = h->POST(body);

    if (code <= 0) {
        Serial.printf("[HTTP] Equipment POST error: %s\n",
                      HTTPClient::errorToString(code).c_str());
        delete h; return false;
    }

    String resp = h->getString();
    delete h;

    if (code != 200 && code != 201) {
        Serial.printf("[HTTP] Equipment HTTP %d: %s\n", code, resp.c_str());
        return false;
    }

    // Aplicar config devuelta por el servidor
    DynamicJsonDocument respDoc(256);
    if (!deserializeJson(respDoc, resp)) {
        JsonObject cfg = respDoc["config"];
        if (!cfg.isNull()) {
            if (cfg.containsKey("refresh_freq_s"))
                outRefreshS = cfg["refresh_freq_s"].as<uint32_t>();
            if (cfg.containsKey("name") && cfg["name"].as<String>().length())
                outName = cfg["name"].as<String>();
        }
    }

    Serial.printf("[HTTP] Equipment OK — refresh:%lus\n",
                  (unsigned long)outRefreshS);
    return true;
}

// ─── POST /api/lora/ingest ────────────────────────────────────────────────────
bool postIngest(const String& serverUrl,
                const String& devAddrHex,
                float freqMhz, uint8_t sf,
                const String& payloadHex) {
    DynamicJsonDocument doc(384);
    doc["gateway_id"]  = devAddrHex;
    doc["rssi"]        = 0;
    doc["snr"]         = 0.0f;
    doc["freq_mhz"]    = freqMhz;
    doc["sf"]          = sf;
    doc["payload_hex"] = payloadHex;

    String body;
    serializeJson(doc, body);

    String url = serverUrl + API_INGEST_ENDPOINT;
    Serial.printf("[HTTP] POST ingest — %d bytes payload\n",
                  (int)payloadHex.length() / 2);

    WiFiClientSecure sc;
    HTTPClient* h = _beginRequest(sc, url);
    int code = h->POST(body);
    String resp = (code > 0) ? h->getString() : "";
    delete h;

    if (code != 200 && code != 201) {
        Serial.printf("[HTTP] Ingest HTTP %d\n", code);
        return false;
    }

    Serial.println("[HTTP] Ingest OK");
    return true;
}
