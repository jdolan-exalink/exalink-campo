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
    String   adminUser;     // usuario admin del portal web
    String   adminPass;     // contraseña admin del portal web
    bool     isPaired;          // true si fue registrado en la app
    String   pairingCode;       // código temporal (vacío si no está en pairing)
    uint32_t pairingExpiresAt;  // epoch time (segundos) de expiración del código
};

class ConfigManager {
public:
    ConfigManager();
    void begin();
    void load(GatewayConfig& cfg);
    void save(const GatewayConfig& cfg);
    void reset();
    static String generateGatewayId();
    static String generatePairingCode();

    // Pairing: genera un código nuevo, lo guarda y devuelve su expiración (epoch s).
    uint32_t startPairing(GatewayConfig& cfg);
    void clearPairing(GatewayConfig& cfg);
    bool isPairingCodeValid(const GatewayConfig& cfg);

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
