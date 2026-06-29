#pragma once
#include <Arduino.h>

struct ClimateReading {
    float temperatureC;
    float humidityPct;
};

ClimateReading readClimate();
