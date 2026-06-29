#include "mp3_player.h"
#include "config.h"
#include <HardwareSerial.h>

// MP3-TF-16P protocol: 0x7E 0xFF 0x06 CMD 0x00 DATA_H DATA_L 0xEF
static HardwareSerial mp3Serial(1);  // UART1

static void mp3SendCmd(uint8_t cmd, uint8_t dataH, uint8_t dataL) {
    uint8_t pkt[] = { 0x7E, 0xFF, 0x06, cmd, 0x00, dataH, dataL, 0xEF };
    mp3Serial.write(pkt, sizeof(pkt));
}

void mp3Init() {
    mp3Serial.begin(9600, SERIAL_8N1, MP3_RX_PIN, MP3_TX_PIN);
    delay(100);
    mp3SetVolume(25);  // default volume
    Serial.printf("[MP3] Init UART1 RX=%d TX=%d\n", MP3_RX_PIN, MP3_TX_PIN);
}

void mp3PlayTrack(uint8_t folder, uint8_t track) {
    mp3SendCmd(0x0F, folder, track);
    Serial.printf("[MP3] Play folder=%d track=%d\n", folder, track);
}

void mp3PlayFile(uint16_t fileNum) {
    mp3SendCmd(0x12, (uint8_t)(fileNum >> 8), (uint8_t)(fileNum & 0xFF));
    Serial.printf("[MP3] Play file=%d\n", fileNum);
}

void mp3Play() {
    mp3SendCmd(0x0D, 0x00, 0x00);
}

void mp3Pause() {
    mp3SendCmd(0x0E, 0x00, 0x00);
}

void mp3Stop() {
    mp3SendCmd(0x16, 0x00, 0x00);
}

void mp3SetVolume(uint8_t vol) {
    if (vol > 30) vol = 30;
    mp3SendCmd(0x06, 0x00, vol);
    Serial.printf("[MP3] Volume=%d\n", vol);
}

void mp3Next() {
    mp3SendCmd(0x01, 0x00, 0x00);
}

void mp3Prev() {
    mp3SendCmd(0x02, 0x00, 0x00);
}

void beep(uint16_t freqHz, uint16_t durationMs) {
    const int channel = 4;
    ledcSetup(channel, freqHz, 8);
    ledcAttachPin(BUZZER_PIN, channel);
    ledcWriteTone(channel, freqHz);
    delay(durationMs);
    ledcWriteTone(channel, 0);
    ledcDetachPin(BUZZER_PIN);
}
