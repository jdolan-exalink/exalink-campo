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
    bool     isProvisioned = false;
};

class ConfigManager {
public:
    void begin();
    void load(ClientConfig& cfg);
    void saveRefreshFreq(uint32_t s);
    void saveName(const String& name);
    void saveDeviceType(const String& type);
    void saveProvisionState(bool provisioned);
    void resetProvision();   // clears isProvisioned → pairing mode on next boot

    // Chip-ID-based identifiers (deterministic)
    static String generateDeviceUid();    // 12-char hex from MAC
    static String generateProvisionCode(); // "XXXX-XXXX" from lower 32 bits
};
