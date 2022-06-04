import pyaudio
import wave
import keyboard
import time
import tkinter as tk
from tkinter import filedialog
from facePoseEstimation import facePoseEstimation
from hrtf import hrtf

def yesno(question):
    # Convenience Function to give T/F to yes no questions
    answer = ''
    yesList = ['y', 'yes', 'true']
    noList = ['n', 'no', 'false']
    invalid = ''
    while not answer:
        answer = input(invalid + question + '[y/n]: ')
        if answer.lower() not in yesList+noList:
            answer = ''
            invalid = 'INVALID RESPONSE: '
 
    if answer in yesList:
        answer = True
    elif answer in noList:
        answer = False
    return answer

def saveWav(recording):
    closing = False
    root = tk.Tk()
    root.withdraw()
    while not closing:
        file = filedialog.asksaveasfile(defaultextension='.wav',
                                            filetypes = [('Wave File', '.wav')])
        if file is None:
            answer = yesno("Are you sure you want to cancel? (Your audio will be deleted)")
            if answer: return
        else:
            closing = True

    with wave.open(file.name, 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(b''.join(recording))

    print('File saved successfully!\n')
    return
        

def main():
    CHUNK = 40
    RATE = 44100
    d2r = 3.14159/180
    p = pyaudio.PyAudio()


    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    iDeviceIndex = 0
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print ("Input Device id [[", i, "]] - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
            deviceName = p.get_device_info_by_host_api_device_index(0, i).get('name')
    #         if 'Realtek' in deviceName:
    #             iDeviceIndex = i
    # print(f'Input device {iDeviceIndex}')
    iDeviceIndex = int(input("Which microphone? (enter ID number): "))
    print()

    output = yesno('Would you like playback while you record?\n[Headsets may output mono, but will record stereo (or just break)]')
    # if output:

        # oDeviceIndex = 0
        # for i in range(0, numdevices):
        #     if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) == 2:
        #         print ("Onput Device id [[", i, "]] - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
        #         deviceName = p.get_device_info_by_host_api_device_index(0, i).get('name')
                # if 'Headphones' in deviceName:
                #     oDeviceIndex = i
    # print(f'Output device {oDeviceIndex}')
    # oDeviceIndex = int(input("Which output? (enter ID number): "))

    stream = p.open(
            rate=RATE,
            channels=2,
            format=pyaudio.paInt16,
            input=True,
            output=output,
            input_device_index=iDeviceIndex,
            # output_device_index=oDeviceIndex,
            frames_per_buffer=CHUNK,
            start=True)

    print()
    print('Stream Opened...')
    time.sleep(0.5)

    recording = []
    sourcePath = []

    print()
    print('Attempting HRTF initialization...')
    time.sleep(0.5)
    hrtfer = hrtf(CHUNK)
    print('HRTF Initialized...')
    time.sleep(0.5)

    # Initialize face tracking
    print()
    print('Attempting FPE Initialization...')
    time.sleep(0.5)
    fpe = facePoseEstimation()
    print('FPE Initialized...')
    time.sleep(0.5)
    print('Attempting to start FPE thread...')
    time.sleep(0.5)
    fpe.start()
    print('FPE thread started...')
    time.sleep(0.5)
    print()



    print('Streaming Start!')
    print('Press [SHIFT + ESC] to stop...')
    while True:
        az, el = fpe.read()
        audio = stream.read(CHUNK, exception_on_overflow=False)
        hrtfer.pazpel = [az*d2r, el*d2r]
        hrtfAudio = hrtfer.convolveHRIR(audio)
        if output:
            stream.write(hrtfAudio)
        recording.append(hrtfAudio)

        try:
            if keyboard.is_pressed('shift+esc'):
                print()
                print('Stopped Recording')
                break
        except:
            continue

    print('Shutting down threads...')
    fpe.stop()

    print()
    certain = False
    saving = yesno('Would you like to save that recording?')
    if not saving:
        certain = yesno('Are you sure? (Your audio will be deleted)')
    if saving or not certain:
        saveWav(recording)

    print()


    return


if __name__ == '__main__':
    another = True
    while another:
        main()
        another = yesno('\nWould you like to record another?')