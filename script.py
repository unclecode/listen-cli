import argparse
import os
import pyaudio
import wave
import time
from io import BytesIO
import numpy as np
from colorama import Fore, Style, init
from pytube import YouTube
from groq import Groq
import requests
import tempfile

# Initialize colorama
init()

# Server endpoint for FastAPI
FAST_API_URL = "https://colab.ngrok.pro/transcribe_stream"

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
THRESHOLD = 1000  # Silence threshold
SILENCE_DURATION = 2  # Duration of silence in seconds to stop recording

# Initialize pyaudio
audio = pyaudio.PyAudio()

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
def transcribe_audio_fast(audio_bytes):
    start_time = time.time()
    response = requests.post(FAST_API_URL, files={"audio": audio_bytes}, data={"initial_prompt": ""}, stream=True)
    end_time = time.time()

    print(Fore.CYAN + "Transcription result:" + Style.RESET_ALL)
    for line in response.iter_lines():
        if line:
            print(line.decode("utf-8"))

    print(Fore.GREEN + f"Total time: {end_time - start_time:.2f} seconds" + Style.RESET_ALL)

# Function to transcribe audio using the Groq SDK

def transcribe_audio_groq(audio_bytes):
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
            transcription = client.audio.transcriptions.create(
                file=(temp_filename, file.read()),
                model="whisper-large-v3",
            )
            print(Fore.CYAN + "Transcription result:" + Style.RESET_ALL)
            print(transcription.text)
    except Exception as e:
        print(Fore.RED + f"Error during transcription: {e}" + Style.RESET_ALL)
    finally:
        os.remove(temp_filename)  # Remove the temporary file
        pass


# Main function
def main(args):
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
        while True:
            frames = record_audio()
            if frames is None:
                break
            audio_bytes = BytesIO()
            wf = wave.open(audio_bytes, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            audio_bytes.seek(0)

    if audio_bytes:
        if args.engine == "groq":
            transcribe_audio_groq(audio_bytes)
        else:
            transcribe_audio_fast(audio_bytes)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio from microphone, file, or YouTube URL using FastAPI server or Groq API.")
    parser.add_argument('--audio-file', type=str, help="Path to the audio file to transcribe.")
    parser.add_argument('--youtube-url', type=str, help="YouTube URL to download and transcribe audio.")
    parser.add_argument('--engine', type=str, choices=['fast', 'groq'], default='fast', help="Transcription engine to use ('fast' or 'groq').")
    parser.add_argument('--save-audio', action='store_true', help="Save the downloaded YouTube audio.")
    args = parser.parse_args()
    main(args)
