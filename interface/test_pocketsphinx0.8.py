from collections import deque
import math
import audioop
import time

__author__ = 'trellet'

import sys,os
import pyaudio
import wave

# hmdir = "/usr/share/pocketsphinx/model/FR/"
dic = '/Users/trellet/Dev/Visual_Analytics/PyMol_Interactive_Plotting/data/ontology.dic'
lm= '/Users/trellet/Dev/Visual_Analytics/PyMol_Interactive_Plotting/data/ontology.lm'



#CHUNK = 1024
CHUNK = 512
#FORMAT = pyaudio.paInt16
FORMAT = pyaudio.paALSA
CHANNELS = 1
RATE = 16000
#RATE = 44100
RECORD_SECONDS = 6

SILENCE_LIMIT = 2  # Silence limit in seconds. The max ammount of seconds where
                   # only silence is recorded. When this time passes the
                   # recording finishes and the file is delivered.

PREV_AUDIO = 0.5  # Previous audio (in seconds) to prepend. When noise
                  # is detected, how much of previously recorded audio is
                  # prepended. This helps to prevent chopping the beggining
                  # of the phrase.
THRESHOLD = 2000  # The threshold intensity that defines silence
                  # and noise signal (an int. lower than THRESHOLD is silence).

num_phrases=2

def decodeSpeech(lm,dic,wavfile):

    import pocketsphinx as ps
    import sphinxbase

    speechRec = ps.Decoder(lm = lm, dict = dic)
    wavFile = file(wavfile,'rb')
    wavFile.seek(44)
    speechRec.decode_raw(wavFile)
    result = speechRec.get_hyp()

    return result[0]


def audio_int(num_samples=50):
    """ Gets average audio intensity of your mic sound. You can use it to get
        average intensities while you're talking and/or silent. The average
        is the avg of the 20% largest intensities recorded.
    """

    print "Getting intensity values from mic."
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    values = [math.sqrt(abs(audioop.avg(stream.read(CHUNK), 4)))
              for x in range(num_samples)]
    values = sorted(values, reverse=True)
    r = sum(values[:int(num_samples * 0.2)]) / int(num_samples * 0.2)
    print " Finished "
    print " Average audio intensity is ", r
    stream.close()
    p.terminate()
    return r


def compute_audio_record(data, p):
    fn = 'output_'+str(int(time.time()))
    wf = wave.open(fn, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(list(prev_audio) + audio2send))
    wf.close()
    wavfile = fn
    recognised = decodeSpeech(lm,dic,wavfile)
    print recognised
    os.remove(fn)
    # cm = 'espeak "'+recognised+'"'
    # os.system(cm)


if __name__ == '__main__':
    # for x in range(10):
    # fn = "o"+str(x)+".wav"

    p = pyaudio.PyAudio()
    print p.get_device_info_by_index(0)['defaultSampleRate']
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print "* Listening mic. "
    audio2send = []
    cur_data = ''  # current chunk  of audio data
    rel = RATE/CHUNK
    slid_win = deque(maxlen=SILENCE_LIMIT * rel)
    #Prepend audio from 0.5 seconds before noise was detected
    prev_audio = deque(maxlen=PREV_AUDIO * rel)
    started = False
    n = num_phrases
    response = []

    while num_phrases == -1 or n > 0:
        cur_data = stream.read(CHUNK)
        slid_win.append(math.sqrt(abs(audioop.avg(cur_data, 4))))
        # print slid_win[-1]
        if sum([x > THRESHOLD for x in slid_win]) > 0:
            if not started:
                print "Starting record of phrase"
                started = True
            audio2send.append(cur_data)
        elif started is True:
            print "Finished"
            # # The limit was reached, finish capture and deliver.
            compute_audio_record(list(prev_audio) + audio2send, p)
            # # Send file to Google and get response
            # r = stt_google_wav(filename)
            # if num_phrases == -1:
            #     print "Response", r
            # else:
            #     response.append(r)
            # # Remove temp file. Comment line to review.
            # os.remove(filename)
            # Reset all
            started = False
            slid_win = deque(maxlen=SILENCE_LIMIT * rel)
            prev_audio = deque(maxlen=0.5 * rel)
            audio2send = []
            n -= 1
            print "Listening ..."
        else:
            prev_audio.append(cur_data)

    stream.stop_stream()
    stream.close()
    p.terminate()
    # print("* recording")
    # frames = []
    # print str(RATE / CHUNK * RECORD_SECONDS) + " size\n"
    # for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    #     data = stream.read(CHUNK)
    #     frames.append(data)
    # print("* done recording")
    # stream.stop_stream()
    # stream.close()
