#pragma once
#include <Arduino.h>

struct ClientConfig {
    String   wifiSsid;
    String   wifiPass;
    String   serverUrl;
    String   deviceName;
    String   deviceType;
    String   hwVersion;
    uint32_t refreshFreqS = 60;
};

class ConfigManager {
public:
    void begin();
    void load(ClientConfig& cfg);
    void saveRefreshFreq(uint32_t s);
    void saveName(const String& name);
    void saveDeviceType(const String& type);
};
