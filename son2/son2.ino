#include <Audio.h>
#include "myfreq.h"

int freq_em = 0; 

// Objets audio
AudioInputI2S in;
AudioOutputI2S out;
AudioControlSGTL5000 audioShield;
AudioAnalyzeNoteFrequency notefreq;
myfreq myFreq;

// Connexions audio
AudioConnection patchCord1(in, 0, notefreq, 0);
// DSP -> sortie
AudioConnection patchCord2(myFreq, 0, out, 0);
AudioConnection patchCord3(myFreq, 0, out, 1);

void setup() {
  Serial.begin(9600);
  AudioMemory(30); // Augmenté pour l'analyse de fréquence
  
  audioShield.enable();
  audioShield.inputSelect(AUDIO_INPUT_MIC);
  audioShield.micGain(10); // en dB
  audioShield.volume(0.5);
  
  // Initialisation de l'analyseur de fréquence
  notefreq.begin(0.15); // Seuil de probabilité (0.0 à 1.0)

  myFreq.setParamValue("freq", freq_em);
}

void loop() {
  if (notefreq.available()) {
    float freq = notefreq.read();
 
    
    Serial.print("Fréquence: ");
    Serial.print(freq);
    Serial.println(" Hz");}

  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n'); // lire jusqu'au retour ligne
    line.trim(); // supprime \r ou espaces
    int freq_em = line.toInt();

    if (freq_em != 0){
      myFreq.setParamValue("freq", freq_em);
      delay(800);
      freq_em = 0;
       myFreq.setParamValue("freq", freq_em);
    }
}
  delay(100); // Lecture toutes les 100ms
  }
  
  