#include "MyDsp.h"

#define AUDIO_OUTPUTS 1

#define MULT_16 32767

MyDsp::MyDsp() : 
AudioStream(1, new audio_block_t*[1]), 
echo(AUDIO_SAMPLE_RATE_EXACT,10000)
{
  echo.setDel(10000);
  echo.setFeedback(0.5);
}


void MyDsp::update(void) {

  audio_block_t* in = receiveReadOnly(0);
  if (!in) return;

  audio_block_t* out = allocate();
  if (!out) {
    release(in);
    return;
  }

  for (int i = 0; i < AUDIO_BLOCK_SAMPLES; i++) {
    out->data[i] = in->data[i];
  }

  transmit(out, 0);

  release(in);
  release(out);
}
