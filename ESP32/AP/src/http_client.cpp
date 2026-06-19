#include "http_client.h"
#include "config.h"
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <WiFi.h>

static const char* _mtypeStr(uint8_t mtype) {
    switch (mtype) {
        case 0x00: return "join_request";
        case 0x20: return "join_accept";
        case 0x40: return "unconf_up";
        case 0x60: return "unconf_down";
        case 0x80: return "conf_up";
        case 0xA0: return "conf_down";
        case 0xC0: return "rejoin";
        default:   return "proprietary";
    }
}

bool httpPostLoRaPacket(
    const String&     serverUrl,
    const String&     gatewayId,
    const String&     lorawanPass,
    const LoRaPacket& pkt,
    float             freqMhz,
    uint8_t           sf,
    float             bwKhz
) {
    if (serverUrl.isEmpty()) {
        Serial.println("[HTTP] Sin URL de servidor configurada.");
        return false;
    }

    // Buffer generoso: payload_hex + payload_b64 + payload_json pueden ser largos
    DynamicJsonDocument doc(1536);
    doc["gateway_id"]  = gatewayId;
    doc["received_at"] = pkt.timestamp;
    doc["rssi"]        = pkt.rssi;
    doc["snr"]         = serialized(String(pkt.snr, 2));
    doc["freq_mhz"]    = freqMhz;
    doc["sf"]          = sf;
    doc["bw_khz"]      = bwKhz;
    doc["payload_hex"] = pkt.payloadHex;
    doc["payload_b64"] = pkt.payloadB64;
    if (pkt.payloadText.startsWith("{")) {
        doc["payload_json"] = pkt.payloadText;
    }

    if (pkt.isLoRaWAN) {
        JsonObject lw = doc.createNestedObject("lorawan");
        lw["mtype"]     = pkt.mtype;
        lw["mtype_str"] = _mtypeStr(pkt.mtype);
        if (pkt.mtype == 0x40 || pkt.mtype == 0x80) {
            char devAddr[9];
            snprintf(devAddr, sizeof(devAddr), "%08X", pkt.devAddr);
            lw["dev_addr"] = devAddr;
            lw["fcnt"]     = pkt.fcnt;
        }
    }

    String body;
    serializeJson(doc, body);

    String url = serverUrl + SERVER_ENDPOINT;
    Serial.printf("[HTTP] POST %s  (%d bytes)\n", url.c_str(), (int)body.length());

    HTTPClient http;
    WiFiClientSecure secureClient;
    if (serverUrl.startsWith("https://")) {
        secureClient.setInsecure();   // red LAN privada — sin verificación de cert
        http.begin(secureClient, url);
    } else {
        http.begin(url);
    }
    http.addHeader("Content-Type", "application/json");
    if (!lorawanPass.isEmpty())
        http.addHeader("Authorization", "Bearer " + lorawanPass);
    http.setTimeout(HTTP_TIMEOUT_MS);

    int code = http.POST(body);

    if (code > 0) {
        Serial.printf("[HTTP] Respuesta %d\n", code);
        http.end();
        return (code == 200 || code == 201 || code == 204);
    } else {
        Serial.printf("[HTTP] Error: %s\n", HTTPClient::errorToString(code).c_str());
        http.end();
        return false;
    }
}
