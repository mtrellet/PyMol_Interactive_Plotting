__author__ = 'trellet'

import sys,os
import pyaudio
import wave

# hmdir = "/usr/share/pocketsphinx/model/FR/"
dic = '/Users/trellet/Dev/Visual_Analytics/PyMol_Interactive_Plotting/data/ontology.dic'
lm= '/Users/trellet/Dev/Visual_Analytics/PyMol_Interactive_Plotting/data/ontology.lm'

def decodeSpeech(lm,dic,wavfile):

    import pocketsphinx as ps
    import sphinxbase

    speechRec = ps.Decoder(lm = lm, dict = dic)
    wavFile = file(wavfile,'rb')
    wavFile.seek(44)
    speechRec.decode_raw(wavFile)
    result = speechRec.get_hyp()

    return result[0]

#CHUNK = 1024
CHUNK = 512
#FORMAT = pyaudio.paInt16
FORMAT = pyaudio.paALSA
CHANNELS = 1
RATE = 16000
#RATE = 44100
RECORD_SECONDS = 6

for x in range(10):
    fn = "o"+str(x)+".wav"
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    print("* recording")
    frames = []
    print str(RATE / CHUNK * RECORD_SECONDS) + " size\n"
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    print("* done recording")
    stream.stop_stream()
    stream.close()
    wf = wave.open(fn, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    p.terminate()
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    wavfile = fn
    recognised = decodeSpeech(lm,dic,wavfile)
    print recognised
    os.remove(fn)
    # cm = 'espeak "'+recognised+'"'
    # os.system(cm)