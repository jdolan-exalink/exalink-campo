#pragma once
#include <Arduino.h>

void mp3Init();
void mp3PlayTrack(uint8_t folder, uint8_t track);
void mp3PlayFile(uint16_t fileNum);
void mp3Play();
void mp3Pause();
void mp3Stop();
void mp3SetVolume(uint8_t vol);  // 0-30
void mp3Next();
void mp3Prev();

void beep(uint16_t freqHz, uint16_t durationMs);
