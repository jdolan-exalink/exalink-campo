#include "config_manager.h"

ConfigManager::ConfigManager() {}

void ConfigManager::begin() {
    _prefs.begin(NVS_NAMESPACE, false);
}

void ConfigManager::load(GatewayConfig& cfg) {
    bool initialized = _prefs.getBool(NVS_KEY_INIT, false);

    if (!initialized) {
        cfg.wifiSsid    = WIFI_DEFAULT_SSID;
        cfg.wifiPass    = WIFI_DEFAULT_PASS;
        cfg.serverUrl   = SERVER_DEFAULT_URL;
        cfg.gatewayId   = generateGatewayId();
        cfg.loraFreq    = LORA_FREQ_DEFAULT;
        cfg.lorawanPass     = LORAWAN_DEFAULT_PASS;
        cfg.listenPort      = LORAWAN_LISTEN_PORT_DEFAULT;
        cfg.syncIntervalMin = GW_SYNC_INTERVAL_DEFAULT_MIN;
        cfg.gatewayName     = "GW-EXA";
        save(cfg);
        _prefs.putBool(NVS_KEY_INIT, true);
    } else {
        cfg.wifiSsid    = _prefs.getString(NVS_KEY_SSID,      WIFI_DEFAULT_SSID);
        cfg.wifiPass    = _prefs.getString(NVS_KEY_PASS,      WIFI_DEFAULT_PASS);
        cfg.serverUrl   = _prefs.getString(NVS_KEY_SERVER,    SERVER_DEFAULT_URL);
        cfg.gatewayId   = _prefs.getString(NVS_KEY_GW_ID,     generateGatewayId());
        cfg.loraFreq    = _prefs.getFloat(NVS_KEY_FREQ,       LORA_FREQ_DEFAULT);
        cfg.lorawanPass     = _prefs.getString(NVS_KEY_LORA_PASS,    LORAWAN_DEFAULT_PASS);
        cfg.listenPort      = _prefs.getUShort(NVS_KEY_LISTEN_PORT,  LORAWAN_LISTEN_PORT_DEFAULT);
        cfg.gatewayName     = _prefs.getString(NVS_KEY_GW_NAME,      "GW-EXA");
        cfg.syncIntervalMin = _prefs.getUShort(NVS_KEY_SYNC_INTERVAL, GW_SYNC_INTERVAL_DEFAULT_MIN);

        // Migración: regenerar IDs del formato viejo "GW-XXXX" (< 16 chars)
        if (cfg.gatewayId.length() < 16) {
            cfg.gatewayId = generateGatewayId();
            _prefs.putString(NVS_KEY_GW_ID, cfg.gatewayId);
            Serial.printf("[Config] ID migrado al nuevo formato: %s\n", cfg.gatewayId.c_str());
        }

        // Migración: actualizar URL vieja al nuevo default
        if (cfg.serverUrl == "http://192.168.1.100:8080") {
            cfg.serverUrl = SERVER_DEFAULT_URL;
            _prefs.putString(NVS_KEY_SERVER, cfg.serverUrl);
            Serial.println("[Config] URL migrada al nuevo servidor.");
        }
    }
}

void ConfigManager::save(const GatewayConfig& cfg) {
    _prefs.putString(NVS_KEY_SSID,      cfg.wifiSsid);
    _prefs.putString(NVS_KEY_PASS,      cfg.wifiPass);
    _prefs.putString(NVS_KEY_SERVER,    cfg.serverUrl);
    _prefs.putString(NVS_KEY_GW_ID,     cfg.gatewayId);
    _prefs.putFloat(NVS_KEY_FREQ,       cfg.loraFreq);
    _prefs.putString(NVS_KEY_LORA_PASS,    cfg.lorawanPass);
    _prefs.putUShort(NVS_KEY_LISTEN_PORT,  cfg.listenPort);
    _prefs.putString(NVS_KEY_GW_NAME,      cfg.gatewayName);
    _prefs.putUShort(NVS_KEY_SYNC_INTERVAL, cfg.syncIntervalMin);
    _prefs.putBool(NVS_KEY_INIT,         true);
    Serial.println("[Config] Configuracion guardada en NVS.");
}

void ConfigManager::reset() {
    _prefs.clear();
    Serial.println("[Config] NVS borrado. Se usaran valores por defecto al reiniciar.");
}

String ConfigManager::generateGatewayId() {
    uint32_t r1 = esp_random();
    uint32_t r2 = esp_random();
    char buf[18];
    snprintf(buf, sizeof(buf), "%08X%08X", r1, r2);
    return String(buf);
}

bool ConfigManager::hasPendingWifi() {
    _prefs.begin(NVS_NAMESPACE, true);
    bool p = _prefs.getBool(NVS_KEY_WIFI_PENDING, false);
    _prefs.end();
    return p;
}

void ConfigManager::savePendingWifi(const String& newSsid, const String& newPass,
                                     const String& oldSsid, const String& oldPass) {
    _prefs.begin(NVS_NAMESPACE, false);
    _prefs.putString(NVS_KEY_SSID_BAK,      oldSsid);
    _prefs.putString(NVS_KEY_PASS_BAK,      oldPass);
    _prefs.putString(NVS_KEY_SSID,          newSsid);
    _prefs.putString(NVS_KEY_PASS,          newPass);
    _prefs.putBool(NVS_KEY_WIFI_PENDING,    true);
    _prefs.end();
    Serial.printf("[Config] WiFi pendiente: '%s' (backup: '%s')\n",
                  newSsid.c_str(), oldSsid.c_str());
}

void ConfigManager::commitPendingWifi() {
    _prefs.begin(NVS_NAMESPACE, false);
    _prefs.putBool(NVS_KEY_WIFI_PENDING, false);
    _prefs.remove(NVS_KEY_SSID_BAK);
    _prefs.remove(NVS_KEY_PASS_BAK);
    _prefs.end();
    Serial.println("[Config] WiFi confirmado.");
}

void ConfigManager::revertWifi(GatewayConfig& cfg) {
    _prefs.begin(NVS_NAMESPACE, false);
    cfg.wifiSsid = _prefs.getString(NVS_KEY_SSID_BAK, WIFI_DEFAULT_SSID);
    cfg.wifiPass = _prefs.getString(NVS_KEY_PASS_BAK, WIFI_DEFAULT_PASS);
    _prefs.putString(NVS_KEY_SSID,          cfg.wifiSsid);
    _prefs.putString(NVS_KEY_PASS,          cfg.wifiPass);
    _prefs.putBool(NVS_KEY_WIFI_PENDING,    false);
    _prefs.remove(NVS_KEY_SSID_BAK);
    _prefs.remove(NVS_KEY_PASS_BAK);
    _prefs.end();
    Serial.printf("[Config] WiFi revertido a '%s'.\n", cfg.wifiSsid.c_str());
}
