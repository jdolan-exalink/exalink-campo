#pragma once
#include <Arduino.h>
#include <WebServer.h>
#include <WiFi.h>
#include "config_manager.h"
#include "lora_manager.h"

class WebPortal {
public:
    WebPortal(ConfigManager& cfgMgr,
              GatewayConfig& gwCfg,
              LoRaManager&   lora);

    void begin();
    void handle();
    bool shouldRestart() const;

    void setServerOk(bool ok, int32_t latencyMs = -1);
    bool isServerOk()     const;
    bool isServerTested() const;

    void incDailyPkt(bool ok);    // incrementa contadores diarios (llamar tras cada envío)
    void resetDailyStats();        // resetear al cambiar de día

    bool shouldForceSync() const;
    void clearForceSync();

private:
    WebServer      _server;
    ConfigManager& _cfgMgr;
    GatewayConfig& _gwCfg;
    LoRaManager&   _lora;
    bool           _restart;
    bool           _serverOk;
    bool           _serverTested;
    int32_t        _lastSyncLatencyMs;
    bool           _forceSyncPending;
    uint32_t       _dayPktsAttempted;
    uint32_t       _dayPktsSent;

    void _handleRoot();
    void _handleStatus();
    void _handleScan();
    void _handleSave();
    void _handleReset();
    void _handleTestServer();
    void _handleWifiApply();
    void _handleForceSync();
    void _handleNotFound();

    static const char _HTML[] PROGMEM;
};
