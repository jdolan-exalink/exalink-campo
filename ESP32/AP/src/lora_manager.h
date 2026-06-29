#pragma once
#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include "config.h"

struct LoRaPacket {
    String   payloadHex;   // bytes recibidos como string hex
    String   payloadB64;   // PHY frame en base64 (para reenvío al servidor)
    String   payloadText;  // payload recibido como texto, si es imprimible/JSON
    int      rssi;
    float    snr;
    uint32_t timestamp;
    // LoRaWAN — válido sólo si isLoRaWAN == true
    bool     isLoRaWAN;
    uint8_t  mtype;        // MHDR & 0xE0 (tipo de mensaje)
    uint32_t devAddr;      // DevAddr para uplinks (mtype 0x40 / 0x80)
    uint16_t fcnt;         // FCnt (16 bits bajos) para uplinks
};

class LoRaManager {
public:
    LoRaManager();

    bool     begin(float freq);
    bool     available();
    LoRaPacket getPacket();
    uint32_t getPacketCount() const;
    float    getFreq()        const;

private:
    SPIClass _spi;   // HSPI (SPI3) con pines explícitos — debe ir ANTES de _radio
    SX1262   _radio;
    uint32_t _pktCount;
    float    _freq;

    static volatile bool _rxFlag;
    static void IRAM_ATTR _onDio1();

    static String _toHex(const String& data);
    static String _toB64(const String& data);
    static void   _parseLoRaWAN(LoRaPacket& pkt, const String& raw);
};
