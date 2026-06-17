#pragma once
#include <Arduino.h>
#include "lora_manager.h"

bool httpPostLoRaPacket(
    const String&     serverUrl,
    const String&     gatewayId,
    const String&     lorawanPass,
    const LoRaPacket& pkt,
    float             freqMhz,
    uint8_t           sf,
    float             bwKhz
);
