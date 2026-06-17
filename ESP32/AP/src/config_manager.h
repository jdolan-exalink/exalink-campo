#pragma once
#include <Arduino.h>
#include <Preferences.h>
#include "config.h"

struct GatewayConfig {
    String   wifiSsid;
    String   wifiPass;
    String   serverUrl;
    String   gatewayId;
    String   gatewayName;   // nombre asignado por el servidor (vacío si no tiene)
    float    loraFreq;
    String   lorawanPass;
    uint16_t listenPort;
    uint16_t syncIntervalMin;   // intervalo de sincronización con servidor (minutos)
};

class ConfigManager {
public:
    ConfigManager();
    void begin();
    void load(GatewayConfig& cfg);
    void save(const GatewayConfig& cfg);
    void reset();
    static String generateGatewayId();

    // Pending WiFi: guarda nuevas creds y respalda las actuales.
    // En el próximo boot se prueban; si fallan se revierte solo.
    bool hasPendingWifi();
    void savePendingWifi(const String& newSsid, const String& newPass,
                         const String& oldSsid, const String& oldPass);
    void commitPendingWifi();          // nueva red OK — limpia backup
    void revertWifi(GatewayConfig& cfg); // nueva red falló — restaura backup

private:
    Preferences _prefs;
};
