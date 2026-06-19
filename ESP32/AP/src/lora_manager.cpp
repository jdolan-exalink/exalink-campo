#include "lora_manager.h"

volatile bool LoRaManager::_rxFlag = false;

void IRAM_ATTR LoRaManager::_onDio1() {
    _rxFlag = true;
}

LoRaManager::LoRaManager()
    : _spi(HSPI)
    , _radio(new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY, _spi))
    , _pktCount(0)
    , _freq(LORA_FREQ_DEFAULT)
{}

bool LoRaManager::begin(float freq) {
    _freq = freq;

    // HSPI (SPI3) con pines explícitos — evita "no default pins on S3"
    _spi.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

    Serial.printf("[LoRa] Inicializando SX1262 en %.1f MHz...\n", freq);

    int state = _radio.begin(
        freq,
        LORA_BW_DEFAULT,
        LORA_SF_DEFAULT,
        LORA_CR_DEFAULT,
        LORA_SYNC_WORD,
        LORA_TX_POWER,
        LORA_PREAMBLE_LEN,
        LORA_TCXO_VOLTAGE
    );

    if (state != RADIOLIB_ERR_NONE) {
        Serial.printf("[LoRa] ERROR begin(): %d\n", state);
        return false;
    }

    // DIO2 controla el switch RF en la Heltec V3 — imprescindible
    _radio.setDio2AsRfSwitch(true);
    _radio.setDio1Action(_onDio1);

    state = _radio.startReceive();
    if (state != RADIOLIB_ERR_NONE) {
        Serial.printf("[LoRa] ERROR startReceive(): %d\n", state);
        return false;
    }

    Serial.printf("[LoRa] OK — escuchando en %.1f MHz (sync 0x%02X)\n",
                  freq, LORA_SYNC_WORD);
    return true;
}

bool LoRaManager::available() {
    return _rxFlag;
}

LoRaPacket LoRaManager::getPacket() {
    _rxFlag = false;

    LoRaPacket pkt;
    pkt.timestamp  = millis();
    pkt.rssi       = 0;
    pkt.snr        = 0.0f;
    pkt.payloadText = "";
    pkt.isLoRaWAN  = false;
    pkt.mtype      = 0;
    pkt.devAddr    = 0;
    pkt.fcnt       = 0;

    String raw;
    int state = _radio.readData(raw);

    if (state == RADIOLIB_ERR_NONE) {
        pkt.payloadHex = _toHex(raw);
        pkt.payloadB64 = _toB64(raw);
        pkt.payloadText = raw;
        pkt.rssi       = _radio.getRSSI();
        pkt.snr        = _radio.getSNR();
        _pktCount++;

        _parseLoRaWAN(pkt, raw);

        Serial.printf("[LoRa] PKT #%lu | RSSI:%d dBm | SNR:%.1f dB | %d bytes | LoRaWAN:%s\n",
                      (unsigned long)_pktCount,
                      pkt.rssi, pkt.snr,
                      (int)raw.length(),
                      pkt.isLoRaWAN ? "si" : "no");
        Serial.printf("[LoRa] HEX: %s\n", pkt.payloadHex.c_str());
        if (pkt.payloadText.startsWith("{")) {
            Serial.printf("[LoRa] JSON: %s\n", pkt.payloadText.c_str());
        }
    } else {
        Serial.printf("[LoRa] Error al leer paquete: %d\n", state);
    }

    _radio.startReceive();
    return pkt;
}

uint32_t LoRaManager::getPacketCount() const { return _pktCount; }
float    LoRaManager::getFreq()        const { return _freq; }

// ─── helpers ──────────────────────────────────────────────────────────────────

String LoRaManager::_toHex(const String& data) {
    String hex;
    hex.reserve(data.length() * 2);
    for (size_t i = 0; i < data.length(); i++) {
        char buf[3];
        snprintf(buf, sizeof(buf), "%02X", (uint8_t)data[i]);
        hex += buf;
    }
    return hex;
}

static const char B64[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

String LoRaManager::_toB64(const String& data) {
    const uint8_t* src = (const uint8_t*)data.c_str();
    size_t len = data.length();
    String out;
    out.reserve(((len + 2) / 3) * 4);
    for (size_t i = 0; i < len; i += 3) {
        uint32_t v = ((uint32_t)src[i] << 16) |
                     (i + 1 < len ? (uint32_t)src[i + 1] << 8 : 0) |
                     (i + 2 < len ? (uint32_t)src[i + 2]      : 0);
        out += B64[(v >> 18) & 0x3F];
        out += B64[(v >> 12) & 0x3F];
        out += (i + 1 < len) ? B64[(v >> 6) & 0x3F] : '=';
        out += (i + 2 < len) ? B64[v        & 0x3F] : '=';
    }
    return out;
}

void LoRaManager::_parseLoRaWAN(LoRaPacket& pkt, const String& raw) {
    size_t len = raw.length();
    // Mínimo absoluto: MHDR(1) + payload + MIC(4) = 5 bytes
    if (len < 5) return;

    uint8_t mhdr  = (uint8_t)raw[0];
    uint8_t major = mhdr & 0x03;
    uint8_t mtype = mhdr & 0xE0;

    if (major != 0) return;  // LoRaWAN major version != 0 → no es LoRaWAN

    // Join Request: 23 bytes exactos (MHDR+AppEUI+DevEUI+DevNonce+MIC)
    // Data uplink:  mínimo 12 bytes (MHDR+FHDR+MIC, sin FPort/FRMPayload)
    bool couldBeJoin = (mtype == 0x00 && len == 23);
    bool couldBeData = ((mtype == 0x40 || mtype == 0x80) && len >= 12);
    bool couldBeJoinAccept = (mtype == 0x20 && len >= 13);

    if (!couldBeJoin && !couldBeData && !couldBeJoinAccept) return;

    pkt.isLoRaWAN = true;
    pkt.mtype     = mtype;

    // Para data uplinks extraer DevAddr y FCnt del FHDR
    if (couldBeData) {
        // FHDR empieza en byte 1: DevAddr[4] FCtrl[1] FCnt[2] FOpts[0-15]
        pkt.devAddr = ((uint32_t)(uint8_t)raw[4] << 24) |
                      ((uint32_t)(uint8_t)raw[3] << 16) |
                      ((uint32_t)(uint8_t)raw[2] <<  8) |
                       (uint32_t)(uint8_t)raw[1];
        pkt.fcnt    = ((uint16_t)(uint8_t)raw[7] << 8) |
                       (uint16_t)(uint8_t)raw[6];
    }
}
