#pragma once
#include <Arduino.h>

struct GatewayStatus {
    double   lat;
    double   lon;
    bool     gpsValid;
    int      wifiRssi;
    String   wifiSsid;
    float    batteryPct;   // <0 si no disponible → se envía 0
    uint32_t uptimeSec;
    uint32_t pktsTotal;
    String   name;         // nombre actual del gateway
    bool     isPaired;          // true si ya fue registrado en la app
    String   pairingCode;       // código temporal (vacío si no está en pairing)
    uint32_t pairingExpiresAt;  // epoch seconds, 0 si no aplica
};

// Sincroniza con el servidor. Si el servidor tiene un nombre asignado
// para este gateway, lo escribe en outName y devuelve true.
bool syncGateway(const String&        serverUrl,
                 const String&        gatewayId,
                 const String&        lorawanPass,
                 const GatewayStatus& status,
                 String&              outName);

// Lee el % de batería del ADC. Devuelve <0 si no hay batería/no disponible.
float readBatteryPct();
