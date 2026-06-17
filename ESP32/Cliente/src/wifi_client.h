#pragma once
#include <Arduino.h>

class WiFiSTA {
public:
    bool   connectSTA(const String& ssid, const String& pass, uint32_t timeoutMs);
    void   handleReconnect(const String& ssid, const String& pass);
    bool   isConnected() const;
    String getLocalIP() const;
    int    getRSSI() const;
    String getSSID() const;

private:
    String _ssid;
    String _pass;
};
