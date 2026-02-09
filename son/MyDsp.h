
#include "Arduino.h"
#include "AudioStream.h"
#include "Audio.h"

#include "Sine.h"
#include "Echo.h"

class MyDsp : public AudioStream
{
public:
  MyDsp();
  virtual void update(void);

private:
  Echo echo;
};