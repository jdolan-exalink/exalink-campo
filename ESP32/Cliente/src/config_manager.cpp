#include "config_manager.h"
#include "config.h"
#include <Preferences.h>

static Preferences _prefs;

void ConfigManager::begin() {
    _prefs.begin(NVS_NAMESPACE_CLIENT, false);
}

void ConfigManager::load(ClientConfig& cfg) {
    cfg.wifiSsid     = _prefs.getString(NVS_KEY_WIFI_SSID,      WIFI_DEFAULT_SSID);
    cfg.wifiPass     = _prefs.getString(NVS_KEY_WIFI_PASS,      WIFI_DEFAULT_PASS);
    cfg.serverUrl    = _prefs.getString(NVS_KEY_SERVER_URL,     SERVER_DEFAULT_URL);
    cfg.deviceName   = _prefs.getString(NVS_KEY_DEVICE_NAME,    DEVICE_NAME_DEFAULT);
    cfg.deviceType   = _prefs.getString(NVS_KEY_DEVICE_TYPE,    DEVICE_TYPE_DEFAULT);
    cfg.hwVersion    = _prefs.getString(NVS_KEY_HW_VERSION,     HW_VERSION_DEFAULT);
    cfg.refreshFreqS = _prefs.getUInt(  NVS_KEY_REFRESH_FREQ_S, TX_INTERVAL_MS / 1000);
    cfg.isProvisioned = _prefs.getBool( NVS_KEY_IS_PROVISIONED,  false);

    Serial.printf("[Config] SSID:%s  Server:%s  refresh:%lus  name:'%s'  type:'%s'  prov:%s\n",
                  cfg.wifiSsid.c_str(),
                  cfg.serverUrl.c_str(),
                  (unsigned long)cfg.refreshFreqS,
                  cfg.deviceName.c_str(),
                  cfg.deviceType.c_str(),
                  cfg.isProvisioned ? "SI" : "NO");
}

void ConfigManager::saveRefreshFreq(uint32_t s) {
    _prefs.putUInt(NVS_KEY_REFRESH_FREQ_S, s);
}

void ConfigManager::saveName(const String& name) {
    _prefs.putString(NVS_KEY_DEVICE_NAME, name);
}

void ConfigManager::saveDeviceType(const String& type) {
    _prefs.putString(NVS_KEY_DEVICE_TYPE, type);
}

void ConfigManager::saveProvisionState(bool provisioned) {
    _prefs.putBool(NVS_KEY_IS_PROVISIONED, provisioned);
    Serial.printf("[Config] isProvisioned guardado: %s\n", provisioned ? "SI" : "NO");
}

void ConfigManager::resetProvision() {
    _prefs.putBool(NVS_KEY_IS_PROVISIONED, false);
    Serial.println("[Config] Provision reseteado — proximo boot en modo pairing.");
}

String ConfigManager::generateDeviceUid() {
    uint64_t mac = ESP.getEfuseMac();
    char buf[13];
    snprintf(buf, sizeof(buf), "%04X%08X",
             (uint16_t)((mac >> 32) & 0xFFFF),
             (uint32_t)(mac & 0xFFFFFFFF));
    return String(buf);
}

String ConfigManager::generateProvisionCode() {
    uint64_t mac = ESP.getEfuseMac();
    uint32_t lower = (uint32_t)(mac & 0xFFFFFFFF);
    char buf[10];
    snprintf(buf, sizeof(buf), "%04X-%04X",
             (uint16_t)(lower >> 16),
             (uint16_t)(lower & 0xFFFF));
    return String(buf);
}
