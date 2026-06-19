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
        cfg.adminUser       = ADMIN_DEFAULT_USER;
        cfg.adminPass       = ADMIN_DEFAULT_PASS;
        cfg.isProvisioned   = false;
        save(cfg);
    } else {
        cfg.wifiSsid    = _prefs.getString(NVS_KEY_SSID,      WIFI_DEFAULT_SSID);
        cfg.wifiPass    = _prefs.getString(NVS_KEY_PASS,      WIFI_DEFAULT_PASS);
        cfg.serverUrl   = _prefs.getString(NVS_KEY_SERVER,    SERVER_DEFAULT_URL);
        cfg.loraFreq    = _prefs.getFloat(NVS_KEY_FREQ,       LORA_FREQ_DEFAULT);
        cfg.lorawanPass     = _prefs.getString(NVS_KEY_LORA_PASS,    LORAWAN_DEFAULT_PASS);
        cfg.listenPort      = _prefs.getUShort(NVS_KEY_LISTEN_PORT,  LORAWAN_LISTEN_PORT_DEFAULT);
        cfg.gatewayName     = _prefs.getString(NVS_KEY_GW_NAME,      "GW-EXA");
        cfg.syncIntervalMin = _prefs.getUShort(NVS_KEY_SYNC_INTERVAL, GW_SYNC_INTERVAL_DEFAULT_MIN);
        cfg.adminUser       = _prefs.getString(NVS_KEY_ADMIN_USER,    ADMIN_DEFAULT_USER);
        cfg.adminPass       = _prefs.getString(NVS_KEY_ADMIN_PASS,    ADMIN_DEFAULT_PASS);
        cfg.isProvisioned   = _prefs.getBool(NVS_KEY_IS_PROVISIONED,  false);

        // Gateway ID: always derived from chip ID — ignore stored random IDs
        cfg.gatewayId = generateGatewayId();
        _prefs.putString(NVS_KEY_GW_ID, cfg.gatewayId);

        // Fix: corrupt admin password
        if (cfg.adminPass == "null" || cfg.adminPass.isEmpty()) {
            cfg.adminPass = ADMIN_DEFAULT_PASS;
            _prefs.putString(NVS_KEY_ADMIN_PASS, cfg.adminPass);
            Serial.println("[Config] Contraseña admin reparada a default.");
        }
    }
}

void ConfigManager::save(const GatewayConfig& cfg) {
    bool ok = _prefs.begin(NVS_NAMESPACE, false);
    if (!ok) {
        Serial.println("[Config] ERROR: No se pudo abrir NVS para escritura.");
        return;
    }
    _prefs.putString(NVS_KEY_SSID,      cfg.wifiSsid);
    _prefs.putString(NVS_KEY_PASS,      cfg.wifiPass);
    _prefs.putString(NVS_KEY_SERVER,    cfg.serverUrl);
    _prefs.putString(NVS_KEY_GW_ID,     cfg.gatewayId);
    _prefs.putFloat(NVS_KEY_FREQ,       cfg.loraFreq);
    _prefs.putString(NVS_KEY_LORA_PASS,    cfg.lorawanPass);
    _prefs.putUShort(NVS_KEY_LISTEN_PORT,  cfg.listenPort);
    _prefs.putString(NVS_KEY_GW_NAME,      cfg.gatewayName);
    _prefs.putUShort(NVS_KEY_SYNC_INTERVAL, cfg.syncIntervalMin);
    _prefs.putString(NVS_KEY_ADMIN_USER,    cfg.adminUser);
    _prefs.putString(NVS_KEY_ADMIN_PASS,    cfg.adminPass);
    _prefs.putBool(NVS_KEY_IS_PROVISIONED,  cfg.isProvisioned);
    _prefs.putBool(NVS_KEY_INIT,         true);
    _prefs.end();

    _prefs.begin(NVS_NAMESPACE, true);
    String verify = _prefs.getString(NVS_KEY_SERVER, "NO_ENCONTRADO");
    _prefs.end();
    Serial.printf("[Config] Guardado. serverUrl=%s (verificado=%s)\n",
                  cfg.serverUrl.c_str(), verify.c_str());
}

void ConfigManager::saveProvisionState(bool provisioned) {
    _prefs.begin(NVS_NAMESPACE, false);
    _prefs.putBool(NVS_KEY_IS_PROVISIONED, provisioned);
    _prefs.end();
    Serial.printf("[Config] isProvisioned guardado: %s\n", provisioned ? "true" : "false");
}

void ConfigManager::reset() {
    _prefs.begin(NVS_NAMESPACE, false);
    _prefs.clear();
    _prefs.end();
    Serial.println("[Config] NVS borrado. Se usaran valores por defecto al reiniciar.");
}

String ConfigManager::generateGatewayId() {
    // Use full 48-bit MAC as 12-char hex — deterministic, survives resets
    uint64_t mac = ESP.getEfuseMac();
    char buf[13];
    snprintf(buf, sizeof(buf), "%04X%08X",
             (uint16_t)((mac >> 32) & 0xFFFF),
             (uint32_t)(mac & 0xFFFFFFFF));
    return String(buf);
}

String ConfigManager::generateProvisionCode() {
    // Lower 32 bits of MAC → "XXXX-XXXX"
    uint64_t mac = ESP.getEfuseMac();
    uint32_t lower = (uint32_t)(mac & 0xFFFFFFFF);
    char buf[10];
    snprintf(buf, sizeof(buf), "%04X-%04X",
             (uint16_t)(lower >> 16),
             (uint16_t)(lower & 0xFFFF));
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
