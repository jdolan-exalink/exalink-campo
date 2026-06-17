#include "wifi_client.h"
#include <WiFi.h>
#include <time.h>

bool WiFiSTA::connectSTA(const String& ssid, const String& pass, uint32_t timeoutMs) {
    _ssid = ssid;
    _pass = pass;

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), pass.c_str());

    Serial.printf("[WiFi] Conectando a '%s'...\n", ssid.c_str());

    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < timeoutMs) {
        delay(200);
    }

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[WiFi] Fallo — sin conexión.");
        return false;
    }

    Serial.printf("[WiFi] OK — IP: %s\n", WiFi.localIP().toString().c_str());

    // NTP para timestamps en los posts a la API
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");

    // Modem sleep: mantiene conexión reduciendo consumo
    WiFi.setSleep(true);

    return true;
}

void WiFiSTA::handleReconnect(const String& ssid, const String& pass) {
    if (WiFi.status() == WL_CONNECTED) return;
    Serial.println("[WiFi] Reconectando...");
    WiFi.disconnect();
    WiFi.begin(ssid.c_str(), pass.c_str());
    // No bloqueamos — el estado se revisa en el próximo ciclo
}

bool   WiFiSTA::isConnected() const { return WiFi.status() == WL_CONNECTED; }
String WiFiSTA::getLocalIP()  const { return WiFi.localIP().toString(); }
int    WiFiSTA::getRSSI()     const { return WiFi.RSSI(); }
String WiFiSTA::getSSID()     const { return WiFi.SSID(); }
