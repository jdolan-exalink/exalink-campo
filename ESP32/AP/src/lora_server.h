#pragma once
#include <Arduino.h>
#include <esp_https_server.h>
#include "lora_manager.h"

struct GatewayConfig;

class LoraServer {
public:
    LoraServer(const GatewayConfig& cfg, LoRaManager& lora);
    ~LoraServer();

    bool begin();
    void stop();
    bool isRunning() const;

private:
    httpd_handle_t       _server;
    const GatewayConfig& _cfg;
    LoRaManager&         _lora;
    bool                 _running;

    static esp_err_t _handleIngest(httpd_req_t *req);
    static esp_err_t _handleHealth(httpd_req_t *req);
};
