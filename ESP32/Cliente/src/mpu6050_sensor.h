#pragma once
#include <Arduino.h>

struct MpuReading {
    float ax, ay, az;   // aceleración en g
    float tempC;        // temperatura interna del chip
    bool  valid;
};

void        initMpu6050();
MpuReading  readMpu6050(uint8_t sensorIdx);  // 0 or 1
