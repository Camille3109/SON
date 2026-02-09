#include <Audio.h>

// Objets audio
AudioInputI2S in;
AudioOutputI2S out;
AudioControlSGTL5000 audioShield;
AudioAnalyzeNoteFrequency notefreq;

// Connexions audio
AudioConnection patchCord0(in, 0, out, 0);
AudioConnection patchCord1(in, 0, out, 1);
AudioConnection patchCord2(in, 0, notefreq, 0);

void setup() {
  Serial.begin(9600);
  AudioMemory(30); // Augmenté pour l'analyse de fréquence
  
  audioShield.enable();
  audioShield.inputSelect(AUDIO_INPUT_MIC);
  audioShield.micGain(10); // en dB
  audioShield.volume(1);
  
  // Initialisation de l'analyseur de fréquence
  notefreq.begin(0.15); // Seuil de probabilité (0.0 à 1.0)
}

void loop() {
  if (notefreq.available()) {
    float freq = notefreq.read();
    float prob = notefreq.probability();
    
    Serial.print("Fréquence: ");
    Serial.print(freq);
    Serial.print(" Hz");
    Serial.print("  Probabilité: ");
    Serial.println(prob);
  }
  
  delay(100); // Lecture toutes les 100ms
}