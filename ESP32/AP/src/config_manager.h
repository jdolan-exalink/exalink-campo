#pragma once
#include <Arduino.h>
#include <Preferences.h>
#include "config.h"

struct GatewayConfig {
    String   wifiSsid;
    String   wifiPass;
    String   serverUrl;
    String   gatewayId;       // Derived from chip ID — deterministic across resets
    String   gatewayName;
    float    loraFreq;
    String   lorawanPass;
    uint16_t listenPort;
    uint16_t syncIntervalMin;
    String   adminUser;
    String   adminPass;
    bool     isProvisioned;   // true once claimed by a tenant via the provision web
};

class ConfigManager {
public:
    ConfigManager();
    void begin();
    void load(GatewayConfig& cfg);
    void save(const GatewayConfig& cfg);
    void reset();

    // Chip-ID-based identifiers (deterministic — survive factory reset in the server)
    static String generateGatewayId();    // 12-char hex from full MAC
    static String generateProvisionCode(); // "XXXX-XXXX" from lower 32 bits of MAC

    void saveProvisionState(bool provisioned);

    // Pending WiFi rollback
    bool hasPendingWifi();
    void savePendingWifi(const String& newSsid, const String& newPass,
                         const String& oldSsid, const String& oldPass);
    void commitPendingWifi();
    void revertWifi(GatewayConfig& cfg);

private:
    Preferences _prefs;
};
