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

    Serial.printf("[Config] SSID:%s  Server:%s  refresh:%lus  name:'%s'  type:'%s'  hw:'%s'\n",
                  cfg.wifiSsid.c_str(),
                  cfg.serverUrl.c_str(),
                  (unsigned long)cfg.refreshFreqS,
                  cfg.deviceName.c_str(),
                  cfg.deviceType.c_str(),
                  cfg.hwVersion.c_str());
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
