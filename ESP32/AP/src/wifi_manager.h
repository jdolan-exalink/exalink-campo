#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include "config.h"

enum class WifiMode { OFF, STA, AP };

class WiFiManager {
public:
    WiFiManager();

    bool connectSTA(const String& ssid, const String& pass, uint32_t timeoutMs);
    void startAP(const String& ssid);
    void stop();

    bool      isSTAConnected() const;
    bool      isAPActive()     const;
    String    getLocalIP()     const;
    WifiMode  getMode()        const;

    // Llamar en loop() para reconexión automática en modo STA
    void enableReconnect(const String& ssid, const String& pass);
    void handleReconnect();

private:
    WifiMode _mode;
    String   _staSSID, _staPass;
    uint32_t _lastReconnect;
    bool     _reconnectEnabled;
};
