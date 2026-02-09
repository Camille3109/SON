#include <Audio.h>
//#include "MyDsp.h"

AudioInputI2S in;
AudioOutputI2S out;
//MyDsp myDsp;
AudioControlSGTL5000 audioShield;
AudioConnection patchCord0(in,0,out,0);
AudioConnection patchCord1(in,0,out,1);

//AudioConnection patchCord0(in, 0, myDsp, 0);
//AudioConnection patchCord1(myDsp, 0, out, 0);
//AudioConnection patchCord2(myDsp, 0, out, 1);

void setup() {
  Serial.begin(9600);
  AudioMemory(6);
  audioShield.enable();
  audioShield.inputSelect(AUDIO_INPUT_MIC);
  audioShield.micGain(10); // in dB
  audioShield.volume(1);
}

void loop() {
}


