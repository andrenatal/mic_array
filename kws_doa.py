import sys
import os
import numpy as np
import collections
from mic_array import MicArray
#from pixel_ring import pixel_ring
from snowboydetect import SnowboyDetect
import pyaudio
from datetime import datetime, date
from requests import Request, Session
import json



RATE = 16000
CHANNELS = 4
KWS_FRAMES = 100     # ms
DOA_FRAMES = 800    # ms

class RingBuffer(object):
    """Ring buffer to hold audio from PortAudio"""
    def __init__(self, size = 4096):
        self._buf = collections.deque(maxlen=size)

    def extend(self, data):
        """Adds data to the end of buffer"""
        self._buf.extend(data)

    def get(self):
        """Retrieves data from the beginning of buffer and clears it"""
        tmp = bytes(bytearray(self._buf))
        self._buf.clear()
	return tmp

def audio_callback(in_data, frame_count, time_info, status):
            ring_buffer.extend(in_data)
            play_data = chr(0) * len(in_data)
	    return play_data, pyaudio.paContinue


def call_kaldi():
	newFile = open("kaldi.opus", "rb")
	datakaldi = newFile.read()
	url = "https://speaktome.services.mozilla.com"
	resp = Session().post(url, headers={'Content-Type': 'application/octet-stream'}, data=datakaldi)
	#print(resp.status_code)
	#print(resp.text)
	json_object = json.loads(resp.text)
	#print(json_object)
	best_confidence = 0
	best_result = ""
	#print(json_object['data'])
	for item in json_object['data']:
  		if (item['confidence'] > best_confidence):
			best_confidence = item['confidence']
  			best_result = item['text']
	return best_result


def call_gateway(command):
	url = "https://respeaker.mozilla-iot.org/commands"
	resp = Session().post(url, data=json.dumps({'text':command}), headers={'Accept': 'application/json', 'Authorization': 'Bearer eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjhiNzM0NjIxLWE1YTYtNDI4ZS04YzJiLTI5MmRkNDdjYzFmYyJ9.eyJpYXQiOjE1MTI3NTM5OTJ9.lEmwc-hlJMCQg4twTgj9UgnPMhHntMDQHwvoBncUfDXbLVqdG3EfeRRsnYezOiWdt_9_vaxKbtNINFejvlUgYg', 'Content-Type': 'application/json'})
	print(resp.status_code)
	print(resp.text)

detector = SnowboyDetect('snowboy/resources/common.res', 'snowboy/resources/alexa/alexa_02092017.umdl')
detector.SetAudioGain(1)
detector.SetSensitivity('0.5')
ring_buffer = RingBuffer(detector.NumChannels() * detector.SampleRate() * 5)
audio = pyaudio.PyAudio()

def main():
    history = collections.deque(maxlen=int(DOA_FRAMES / KWS_FRAMES))
    recording = False
    try:
        with MicArray(RATE, CHANNELS, RATE * KWS_FRAMES / 1000)  as mic:
            for chunk in mic.read_chunks():
                history.append(chunk)

                # Detect keyword from channel 0
		if not recording:
                	ans = detector.RunDetection(chunk[0::CHANNELS].tostring())
                	if ans > 0:
				newFile = open("kaldi.raw", "wb")
		    		recording = True
				dtstart = datetime.utcnow()
                    		frames = np.concatenate(history)
                    		direction = mic.get_direction(frames)
       				# pixel_ring.set_direction(direction)
                    		print('\n{}'.format(int(direction)))
		else:
                        dtend = datetime.utcnow()
			recordingtime =  (dtend - dtstart).total_seconds()
			print('recording', recordingtime, len(chunk))
			newFileByteArray = bytearray(chunk[0::CHANNELS])
			newFile.write(newFileByteArray)
			if (recordingtime > 3):
				# salva arquivo no disco
				newFile.close()
				# convert para apenas um canal
				os.system("opusenc --raw --raw-rate 16000 --raw-bits 16 --raw-chan 1 --raw-endianness 0 kaldi.raw kaldi.opus")
				# chama kaldi
				kaldi_result = call_kaldi()
				# com o resultado chama o gateway
				print('gocloud', kaldi_result)
				call_gateway(kaldi_result)
				recording = False;

    except KeyboardInterrupt:
        pass

   # pixel_ring.off()

if __name__ == '__main__':
    main()
