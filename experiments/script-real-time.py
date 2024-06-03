import argparse
import os
import pyaudio
import wave
import time
import threading
import queue
from io import BytesIO
import numpy as np
from colorama import Fore, Style, init
from pytube import YouTube
from groq import Groq
import requests
import tempfile
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import webrtcvad
# Initialize colorama
init()

# Server endpoint for FastAPI
from config import FAST_API_URL

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
THRESHOLD = 1000  # Silence threshold
SILENCE_DURATION = 2  # Duration of silence in seconds to stop recording

# Initialize pyaudio
audio = pyaudio.PyAudio()

# Queue for handling transcriptions in order
transcription_queue = queue.PriorityQueue()

# Function to record audio
def record_audio():
    print(Fore.GREEN + "Press Enter to start recording or 'q' to quit..." + Style.RESET_ALL)
    user_input = input()
    if user_input.lower() == 'q':
        print(Fore.RED + "Quitting..." + Style.RESET_ALL)
        return None

    print(Fore.YELLOW + "Recording started..." + Style.RESET_ALL)

    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    silent_chunks = 0

    while True:
        data = stream.read(CHUNK)
        frames.append(data)

        audio_data = np.frombuffer(data, dtype=np.int16)
        if np.max(audio_data) < THRESHOLD:
            silent_chunks += 1
        else:
            silent_chunks = 0

        if silent_chunks > int(SILENCE_DURATION * RATE / CHUNK):
            print(Fore.YELLOW + "Silence detected, stopping recording..." + Style.RESET_ALL)
            break

    stream.stop_stream()
    stream.close()

    return frames

# Function to download audio from YouTube
def download_youtube_audio(url, save_audio=False):
    yt = YouTube(url)
    audio_filename = f"{yt.title}.mp3"
    
    if os.path.isfile(audio_filename):
        print(Fore.YELLOW + "Audio already downloaded." + Style.RESET_ALL)
        # Return audio buffer
        with open(audio_filename, 'rb') as f:
            audio_buffer = BytesIO(f.read())
        return audio_buffer
    
    audio_stream = yt.streams.filter(only_audio=True).first()
    audio_buffer = BytesIO()
    audio_stream.stream_to_buffer(audio_buffer)
    audio_buffer.seek(0)

    if save_audio:
        with open(audio_filename, 'wb') as f:
            f.write(audio_buffer.getbuffer())
        print(Fore.GREEN + f"Audio saved as {audio_filename}" + Style.RESET_ALL)
    
    return audio_buffer

# Function to transcribe audio using the FastAPI server
def transcribe_audio_fast(audio_bytes, index, result_queue):
    start_time = time.time()
    response = requests.post(FAST_API_URL, files={"audio": audio_bytes}, data={"initial_prompt": ""}, stream=True)
    end_time = time.time()

    transcription_text = ""
    for line in response.iter_lines():
        if line:
            transcription_text += line.decode("utf-8") + "\n"
    
    result_queue.put((index, transcription_text))

    print(Fore.GREEN + f"Total time for segment {index}: {end_time - start_time:.2f} seconds" + Style.RESET_ALL)

# Function to transcribe audio using the Groq SDK
def transcribe_audio_groq(audio_bytes, index, result_queue):
    groq_api_key = os.getenv('GROQ_API_KEY')
    if not groq_api_key:
        print(Fore.RED + "Error: GROQ_API_KEY environment variable not set." + Style.RESET_ALL)
        raise EnvironmentError("GROQ_API_KEY environment variable not set.")
    
    client = Groq(api_key=groq_api_key)
    audio_bytes.seek(0)  # Ensure we start reading from the beginning of the BytesIO object

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_file.write(audio_bytes.read())
        temp_filename = tmp_file.name

    try:
        with open(temp_filename, "rb") as file:
            # transcription = client.audio.transcriptions.create(
            #     file=(temp_filename, file.read()),
            #     model="whisper-large-v3",
            # )
            # result_queue.put((index, transcription.text))
            import random
            t = random.randint(1, 50) / 10
            print(Fore.YELLOW + f"Simulating transcription for segment {index}... sleep for {t} seconds" + Style.RESET_ALL)
            time.sleep(t)
            result_queue.put((index, "Test demo for " + str(index)))
    except Exception as e:
        print(Fore.RED + f"Error during transcription: {e}" + Style.RESET_ALL)
    finally:
        os.remove(temp_filename)  # Remove the temporary file

# Real-time recording and transcription function
def real_time_recording(engine, stop_event):
    def transcribe_segment(audio_segment, index):
        audio_bytes = BytesIO()
        wf = wave.open(audio_bytes, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(audio_segment))
        wf.close()
        audio_bytes.seek(0)

        if engine == "groq":
            transcribe_audio_groq(audio_bytes, index, transcription_queue)
        else:
            transcribe_audio_fast(audio_bytes, index, transcription_queue)
    
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    index = 0
    vad = webrtcvad.Vad(2)  # Set aggressiveness level (0-3)
    last_speech_time = time.time()
    SILENCE_THRESHOLD = 700  # Increase silence length to make it less sensitive
    MAX_SILENCE_THRESHOLD = -40  # Less sensitive silence threshold for detect_nonsilent function
    MIN_SPEECH_THRESHOLD = 500  # Minimum amplitude to consider as speech, adjust as needed
    BUFFER_SILENCE_DURATION = 1  # Buffer time for silence in seconds

    while True:
        try:
            data = stream.read(CHUNK)
        except IOError as e:
            if e.errno == -9981:  # Input overflowed
                print(Fore.RED + "Input overflowed. Skipping this chunk." + Style.RESET_ALL)
                continue
            else:
                raise e

        frames.append(data)

       
        # Check if the chunk contains speech
        audio_data = np.frombuffer(data, dtype=np.int16)
        if np.max(audio_data) < MIN_SPEECH_THRESHOLD:
            frames.pop()  # Remove silent chunk
            continue  # Continue capturing if chunk is silent
        

        # Detect silence
        audio_segment = AudioSegment(
            data=b''.join(frames),
            sample_width=audio.get_sample_size(FORMAT),
            frame_rate=RATE,
            channels=CHANNELS
        )
        nonsilent_ranges = detect_nonsilent(audio_segment, min_silence_len=SILENCE_THRESHOLD, silence_thresh=MAX_SILENCE_THRESHOLD)

        if nonsilent_ranges:
            if time.time() - last_speech_time > BUFFER_SILENCE_DURATION:
                last_speech_time = time.time()
                print(Fore.YELLOW + f"Silence detected, processing segment {index}..." + Style.RESET_ALL)
                threading.Thread(target=transcribe_segment, args=(frames, index)).start()
                index += 1
                frames = []
        else:
            if time.time() - last_speech_time > SILENCE_DURATION:
                print(Fore.YELLOW + f"Silence duration exceeded threshold, stopping recording..." + Style.RESET_ALL)
                break

    stream.stop_stream()
    stream.close()
    stop_event.set()

# Function to print transcriptions in order
def print_transcriptions(recording_thread, stop_event):
    expected_index = 0
    try:
        while not stop_event.is_set():
            if not transcription_queue.empty():
                index, transcription = transcription_queue.get()
                if index == expected_index:
                    print(Fore.CYAN + f"Transcription for segment {index}:" + Style.RESET_ALL)
                    print(transcription)
                    expected_index += 1
                else:
                    transcription_queue.put((index, transcription))
    except KeyboardInterrupt:
        print(Fore.RED + "Interrupted. Stopping recording..." + Style.RESET_ALL)
        stop_event.set()
        recording_thread.join()
        print(Fore.GREEN + "Recording stopped." + Style.RESET_ALL)                

# Function to process and print single transcription
def process_single_transcription(engine, audio_bytes):
    result_queue = queue.PriorityQueue()
    if engine == "groq":
        transcribe_audio_groq(audio_bytes, 0, result_queue)
    else:
        transcribe_audio_fast(audio_bytes, 0, result_queue)

    # Print the result
    while not result_queue.empty():
        index, transcription = result_queue.get()
        print(Fore.CYAN + f"Transcription for segment {index}:" + Style.RESET_ALL)
        print(transcription)

# Main function
def main(args):
    stop_event = threading.Event()
    if args.real_time:
        print(Fore.GREEN + "Starting real-time recording and transcription..." + Style.RESET_ALL)
        recording_thread = threading.Thread(target=real_time_recording, args=(args.engine,stop_event))
        recording_thread.start()
        print_transcriptions(recording_thread, stop_event)
    else:
        audio_bytes = None

        if args.audio_file:
            if not os.path.isfile(args.audio_file):
                print(Fore.RED + f"File not found: {args.audio_file}" + Style.RESET_ALL)
                return
            with open(args.audio_file, 'rb') as f:
                audio_bytes = BytesIO(f.read())
        elif args.youtube_url:
            print(Fore.YELLOW + "Downloading audio from YouTube..." + Style.RESET_ALL)
            audio_bytes = download_youtube_audio(args.youtube_url, args.save_audio)
        else:
            frames = record_audio()
            if frames is None:
                return
            audio_bytes = BytesIO()
            wf = wave.open(audio_bytes, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            audio_bytes.seek(0)

        if audio_bytes:
            process_single_transcription(args.engine, audio_bytes)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio from microphone, file, or YouTube URL using FastAPI server or Groq API.")
    parser.add_argument('--audio-file', type=str, help="Path to the audio file to transcribe.")
    parser.add_argument('--youtube-url', type=str, help="YouTube URL to download and transcribe audio.")
    parser.add_argument('--engine', type=str, choices=['fast', 'groq'], default='fast', help="Transcription engine to use ('fast' or 'groq').")
    parser.add_argument('--save-audio', action='store_true', help="Save the downloaded YouTube audio.")
    parser.add_argument('--real-time', action='store_true', help="Enable real-time recording and transcription.")
    args = parser.parse_args()
    
    # Debugging setup
    if os.getenv('DEBUG') == '1':
        args.real_time = True
        args.engine = 'fast'  # or 'groq'
        # args.engine = 'groq'  # or 'groq'

    main(args)    
