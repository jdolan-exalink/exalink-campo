#pragma once
#include <Arduino.h>
#include "mpu6050_sensor.h"

// Obtiene la configuración del dispositivo desde el servidor.
// Devuelve true si el servidor respondió OK.
bool getDeviceConfig(const String& serverUrl,
                     const String& devAddrHex,
                     uint32_t&     outRefreshS,
                     String&       outName,
                     String&       outDevType);

// Reporta estado del equipo. Actualiza outRefreshS y outName con la
// respuesta del servidor (si cambió).
bool postEquipment(const String& serverUrl,
                   const String& devAddrHex,
                   const String& name,
                   const String& devType,
                   double lat, double lon, bool gpsValid,
                   const String& wifiSsid, int wifiRssi,
                   float battery,
                   float temperature,
                   float humidity,
                   const MpuReading& mpu0,
                   const MpuReading& mpu1,
                   uint32_t& outRefreshS,
                   String&   outName);

// Publica un paquete LoRa directamente al servidor (bypass gateway).
bool postIngest(const String& serverUrl,
                const String& devAddrHex,
                float freqMhz, uint8_t sf,
                const String& payloadHex);
