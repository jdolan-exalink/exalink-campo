#include "mpu6050_sensor.h"
#include "config.h"
#include <Wire.h>

// MPU6050 registers
#define MPU6050_PWR_MGMT_1   0x6B
#define MPU6050_ACCEL_XOUT_H 0x3B
#define MPU6050_ACCEL_CONFIG 0x1C
#define MPU6050_WHO_AM_I     0x75

// Two sensors: AD0=LOW (0x68) and AD0=HIGH (0x69)
static const uint8_t _addrs[2] = { 0x68, 0x69 };
static bool _initDone = false;
static bool _sensorOk[2] = { false, false };

static void mpuWriteReg(uint8_t addr, uint8_t reg, uint8_t val) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(val);
    Wire.endTransmission();
}

static bool mpuReadRegs(uint8_t addr, uint8_t reg, uint8_t* buf, uint8_t len) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    if (Wire.endTransmission() != 0) return false;
    uint8_t n = Wire.requestFrom((int)addr, (int)len);
    for (uint8_t i = 0; i < n && i < len; i++) {
        buf[i] = Wire.read();
    }
    return n == len;
}

void initMpu6050() {
    if (_initDone) return;

    // Separate I2C bus: SDA=GPIO4, SCL=GPIO5
    pinMode(MPU6050_SDA_PIN, INPUT_PULLUP);
    pinMode(MPU6050_SCL_PIN, INPUT_PULLUP);
    Wire.begin(MPU6050_SDA_PIN, MPU6050_SCL_PIN);
    delay(100);
    Wire.setClock(400000);

    for (uint8_t i = 0; i < 2; i++) {
        uint8_t addr = _addrs[i];

        uint8_t who = 0;
        if (mpuReadRegs(addr, MPU6050_WHO_AM_I, &who, 1) && who == 0x68) {
            mpuWriteReg(addr, MPU6050_PWR_MGMT_1, 0x00);  // wake up
            delay(100);
            mpuWriteReg(addr, MPU6050_ACCEL_CONFIG, 0x00); // ±2g
            _sensorOk[i] = true;
            Serial.printf("[MPU] Sensor %d OK addr=0x%02X\n", i, addr);
        } else {
            _sensorOk[i] = false;
            Serial.printf("[MPU] Sensor %d NOT FOUND addr=0x%02X WHO=0x%02X\n", i, addr, who);
        }
    }

    _initDone = true;
}

MpuReading readMpu6050(uint8_t sensorIdx) {
    initMpu6050();
    if (sensorIdx >= 2 || !_sensorOk[sensorIdx]) return { 0, 0, 0, 0, false };

    uint8_t addr = _addrs[sensorIdx];
    // Read 8 bytes: ACCEL_X(2) ACCEL_Y(2) ACCEL_Z(2) TEMP(2)
    uint8_t buf[8];
    if (!mpuReadRegs(addr, MPU6050_ACCEL_XOUT_H, buf, 8)) {
        return { 0, 0, 0, 0, false };
    }

    int16_t axRaw = ((int16_t)buf[0] << 8) | buf[1];
    int16_t ayRaw = ((int16_t)buf[2] << 8) | buf[3];
    int16_t azRaw = ((int16_t)buf[4] << 8) | buf[5];
    int16_t tempRaw = ((int16_t)buf[6] << 8) | buf[7];

    float ax = axRaw / 16384.0f;  // ±2g
    float ay = ayRaw / 16384.0f;
    float az = azRaw / 16384.0f;
    float tempC = (tempRaw / 340.0f) + 36.53f;

    return { ax, ay, az, tempC, true };
}
