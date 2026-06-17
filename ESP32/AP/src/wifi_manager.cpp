#include "wifi_manager.h"

WiFiManager::WiFiManager()
    : _mode(WifiMode::OFF)
    , _lastReconnect(0)
    , _reconnectEnabled(false)
{}

bool WiFiManager::connectSTA(const String& ssid, const String& pass,
                              uint32_t timeoutMs) {
    Serial.printf("[WiFi] Conectando a '%s'...\n", ssid.c_str());

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), pass.c_str());

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() - start > timeoutMs) {
            Serial.println("[WiFi] Timeout — conexion fallida.");
            WiFi.disconnect(true);
            _mode = WifiMode::OFF;
            return false;
        }
        delay(500);
        Serial.print(".");
    }
    Serial.println();

    _mode   = WifiMode::STA;
    _staSSID = ssid;
    _staPass = pass;
    Serial.printf("[WiFi] Conectado. IP: %s\n",
                  WiFi.localIP().toString().c_str());
    return true;
}

void WiFiManager::startAP(const String& ssid) {
    Serial.printf("[WiFi] Iniciando AP '%s'...\n", ssid.c_str());

    WiFi.mode(WIFI_AP);

    IPAddress apIP(192, 168, 4, 1);
    IPAddress subnet(255, 255, 255, 0);
    WiFi.softAPConfig(apIP, apIP, subnet);
    WiFi.softAP(ssid.c_str());   // Sin contraseña — portal abierto

    _mode = WifiMode::AP;
    Serial.printf("[WiFi] AP listo. IP: %s\n",
                  WiFi.softAPIP().toString().c_str());
}

void WiFiManager::stop() {
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    _mode = WifiMode::OFF;
}

bool WiFiManager::isSTAConnected() const {
    return (_mode == WifiMode::STA) && (WiFi.status() == WL_CONNECTED);
}

bool WiFiManager::isAPActive() const {
    return _mode == WifiMode::AP;
}

String WiFiManager::getLocalIP() const {
    if (_mode == WifiMode::STA) return WiFi.localIP().toString();
    if (_mode == WifiMode::AP)  return WiFi.softAPIP().toString();
    return "0.0.0.0";
}

WifiMode WiFiManager::getMode() const {
    return _mode;
}

void WiFiManager::enableReconnect(const String& ssid, const String& pass) {
    _staSSID          = ssid;
    _staPass          = pass;
    _reconnectEnabled = true;
}

void WiFiManager::handleReconnect() {
    if (_mode != WifiMode::STA || !_reconnectEnabled) return;
    if (WiFi.status() == WL_CONNECTED) return;

    uint32_t now = millis();
    if (now - _lastReconnect > WIFI_RECONNECT_INTERVAL) {
        _lastReconnect = now;
        Serial.println("[WiFi] Conexion perdida. Reintentando...");
        WiFi.disconnect();
        WiFi.begin(_staSSID.c_str(), _staPass.c_str());
    }
}
