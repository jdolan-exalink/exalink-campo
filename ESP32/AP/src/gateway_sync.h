#pragma once
#include <Arduino.h>

struct GatewayStatus {
    double   lat;
    double   lon;
    bool     gpsValid;
    int      wifiRssi;
    String   wifiSsid;
    float    batteryPct;
    uint32_t uptimeSec;
    uint32_t pktsTotal;
    String   name;
};

struct GatewaySyncResult {
    bool   ok;
    String name;
    bool   isProvisioned;
};

GatewaySyncResult syncGateway(const String&        serverUrl,
                               const String&        gatewayId,
                               const String&        lorawanPass,
                               const GatewayStatus& status);

// Called before factory reset: un-provisions the device on the backend.
// Returns true if backend confirmed the reset (or if no WiFi — caller should
// still proceed with local factory reset).
bool resetDeviceProvision(const String& serverUrl,
                          const String& provisionCode,
                          const String& deviceUid);

float readBatteryPct();
