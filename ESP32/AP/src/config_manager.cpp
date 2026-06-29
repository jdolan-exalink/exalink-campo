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
        cfg.isPaired        = false;
        cfg.pairingCode     = "";
        cfg.pairingExpiresAt = 0;
        save(cfg);
        // NVS_KEY_INIT ya lo escribe save()
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
        cfg.adminUser       = _prefs.getString(NVS_KEY_ADMIN_USER,    ADMIN_DEFAULT_USER);
        cfg.adminPass       = _prefs.getString(NVS_KEY_ADMIN_PASS,    ADMIN_DEFAULT_PASS);
        cfg.isPaired        = _prefs.getBool(NVS_KEY_IS_PAIRED, false);
        cfg.pairingCode     = _prefs.getString(NVS_KEY_PAIR_CODE, "");
        cfg.pairingExpiresAt = _prefs.getUInt(NVS_KEY_PAIR_EXP, 0);

        // Migración: reparar adminPass corrupto ("null" literal de ArduinoJson)
        if (cfg.adminPass == "null" || cfg.adminPass.isEmpty()) {
            cfg.adminPass = ADMIN_DEFAULT_PASS;
            _prefs.putString(NVS_KEY_ADMIN_PASS, cfg.adminPass);
            Serial.println("[Config] Contraseña admin reparada a default.");
        }

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
    _prefs.putBool(NVS_KEY_IS_PAIRED,       cfg.isPaired);
    _prefs.putString(NVS_KEY_PAIR_CODE,     cfg.pairingCode);
    _prefs.putUInt(NVS_KEY_PAIR_EXP,        cfg.pairingExpiresAt);
    _prefs.putBool(NVS_KEY_INIT,         true);
    _prefs.end();

    _prefs.begin(NVS_NAMESPACE, true);
    String verify = _prefs.getString(NVS_KEY_SERVER, "NO_ENCONTRADO");
    _prefs.end();
    Serial.printf("[Config] Guardado en NVS. serverUrl=%s (verificado=%s)\n",
                  cfg.serverUrl.c_str(), verify.c_str());
    if (verify != cfg.serverUrl) {
        Serial.printf("[Config] ¡ADVERTENCIA! NVS no coincide: escrito='%s' leido='%s'\n",
                      cfg.serverUrl.c_str(), verify.c_str());
    }
}

void ConfigManager::reset() {
    _prefs.begin(NVS_NAMESPACE, false);
    _prefs.clear();
    _prefs.end();
    Serial.println("[Config] NVS borrado. Se usaran valores por defecto al reiniciar.");
}

String ConfigManager::generateGatewayId() {
    uint32_t r1 = esp_random();
    uint32_t r2 = esp_random();
    char buf[18];
    snprintf(buf, sizeof(buf), "%08X%08X", r1, r2);
    return String(buf);
}

String ConfigManager::generatePairingCode() {
    char buf[PAIRING_CODE_LEN + 1];
    for (uint8_t i = 0; i < PAIRING_CODE_LEN; i++) {
        buf[i] = '0' + (esp_random() % 10);
    }
    buf[PAIRING_CODE_LEN] = '\0';
    return String(buf);
}

uint32_t ConfigManager::startPairing(GatewayConfig& cfg) {
    cfg.pairingCode      = generatePairingCode();
    cfg.pairingExpiresAt = (uint32_t)(time(nullptr) + (PAIRING_TTL_MIN * 60));
    if (cfg.pairingExpiresAt < 60) {
        cfg.pairingExpiresAt = (uint32_t)(millis() / 1000) + (PAIRING_TTL_MIN * 60);
    }
    cfg.isPaired = false;
    save(cfg);
    Serial.printf("[Config] Pairing code generado: %s (expira %lu)\n",
                  cfg.pairingCode.c_str(), (unsigned long)cfg.pairingExpiresAt);
    return cfg.pairingExpiresAt;
}

void ConfigManager::clearPairing(GatewayConfig& cfg) {
    cfg.pairingCode      = "";
    cfg.pairingExpiresAt = 0;
    save(cfg);
}

bool ConfigManager::isPairingCodeValid(const GatewayConfig& cfg) {
    if (cfg.isPaired || cfg.pairingCode.isEmpty() || cfg.pairingExpiresAt == 0) {
        return false;
    }
    uint32_t now = (uint32_t)time(nullptr);
    if (now < 60) now = (uint32_t)(millis() / 1000);
    return now < cfg.pairingExpiresAt;
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
