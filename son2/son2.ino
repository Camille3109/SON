#include <Audio.h>
#include "myfreq.h"

int freq_em = 0;  // fréquence émise

// Objets audio
AudioInputI2S in;
AudioOutputI2S out;
AudioControlSGTL5000 audioShield; // audioshield
AudioAnalyzeNoteFrequency notefreq; // analyseur de fréquence
myfreq myFreq;

// Connexions audio
// micro -> analyseur
AudioConnection patchCord1(in, 0, notefreq, 0);
// DSP -> sortie
AudioConnection patchCord2(myFreq, 0, out, 0);
AudioConnection patchCord3(myFreq, 0, out, 1);

void setup() {
  Serial.begin(9600);
  AudioMemory(30); // Réserve assez de mémoire pour l'analyse de fréquence
  
  audioShield.enable();
  audioShield.inputSelect(AUDIO_INPUT_MIC);
  audioShield.micGain(10); // en dB
  audioShield.volume(0.5);
  
  // Initialisation de l'analyseur de fréquence
  notefreq.begin(0.15); // seuil minimum de confiance pour accepter la note détectée

  myFreq.setParamValue("choose", 0); // on se place dans la config de base
  myFreq.setParamValue("freq", freq_em); // initialisation de la fréquence émise à 0
}

void loop() {
  if (notefreq.available()) { // si on a détecté une fréquence dans le micro
    float freq = notefreq.read(); // on détecte la fréquence
 
    Serial.print("Fréquence: ");
    Serial.print(freq); // on envoie la fréquence via Serial
    Serial.println(" Hz");}

  if (Serial.available() > 0) { // si une fréquence est envoyée depuis Python
    String line = Serial.readStringUntil('\n'); // lire jusqu'au retour ligne
    line.trim(); // supprime \r ou espaces
    int freq_em = line.toInt(); // la fréquence à émettre est transformée en entier

    if (freq_em != 0){
      if (freq_em == 3000){ // si la fréquence à émettre est 3000
        myFreq.setParamValue("choose", 1); // on active le mode screamer
        myFreq.setParamValue("freq", random(2000, 3000)); // on choisit une fréquece haute
        delay(800);
        freq_em = 0; // on remet les paramètres de base
        myFreq.setParamValue("freq", freq_em);
        myFreq.setParamValue("choose", 0);}
      else {
        myFreq.setParamValue("freq", freq_em); // sinon on émet la fréquence demandée 
        delay(800);
        freq_em = 0;
        myFreq.setParamValue("freq", freq_em);
        
      }
    }
}
  delay(100); // Lecture toutes les 100ms
  }
  


  
  