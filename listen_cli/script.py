import argparse
import os
import pyaudio
import wave
import time
import queue
from io import BytesIO
import numpy as np
from colorama import Fore, Style, init
from pytube import YouTube
from groq import Groq
import requests
import tempfile
from pydub import AudioSegment
from datetime import timedelta
from listen_cli.config import FAST_API_URL
# Initialize colorama
init()

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
THRESHOLD = 1000  # Silence threshold
SILENCE_DURATION = 1  # Duration of silence in seconds to stop recording

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
            print(Fore.GREEN + "Silence detected, stopping recording..." + Style.RESET_ALL)
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
    response = requests.post(FAST_API_URL, files={"audio": audio_bytes}, data={"initial_prompt": ""}, stream=True)

    transcription_text = ""
    for line in response.iter_lines():
        if line:
            transcription_text += line.decode("utf-8") + "\n"
    
    result_queue.put((index, transcription_text))

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
            # start_time = time.time()
            transcription = client.audio.transcriptions.create(
                file=(temp_filename, file.read()),
                model="whisper-large-v3",
            )
            result_queue.put((index, transcription.text))
    except Exception as e:
        print(Fore.RED + f"Error during transcription: {e}" + Style.RESET_ALL)
    finally:
        os.remove(temp_filename)  # Remove the temporary file

# Function to process and print single transcription
def process_single_transcription(engine, audio_bytes, output_file):
    # Convert the audio to WAV format using pydub for duration calculation only
    audio_bytes.seek(0)
    audio_segment = AudioSegment.from_file(audio_bytes)
    duration = len(audio_segment) / 1000  # pydub uses milliseconds

    # Convert duration to hh:mm:ss format
    duration_formatted = str(timedelta(seconds=int(duration)))
    
    print(Fore.YELLOW + f"Processing transcription... Audio duration: {duration_formatted}" + Style.RESET_ALL)

    # Reset audio_bytes to the beginning for transcription
    audio_bytes.seek(0)
    start_time = time.time()
    result_queue = queue.PriorityQueue()
    if engine == "groq":
        transcribe_audio_groq(audio_bytes, 0, result_queue)
    else:
        transcribe_audio_fast(audio_bytes, 0, result_queue)
    end_time = time.time()
    print(Fore.GREEN + f"Total time transcription: {end_time - start_time:.2f} seconds" + Style.RESET_ALL)
    # Print the result
    while not result_queue.empty():
        index, transcription = result_queue.get()        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(transcription + "\n")
            print(Fore.CYAN + f"Transcription is done, and result stored in {output_file}" + Style.RESET_ALL)
        else:
            print(Fore.CYAN + "Transcription result: " + transcription + Style.RESET_ALL)

# Main function
def main():
    parser = argparse.ArgumentParser(description="Transcribe audio from microphone, file, or YouTube URL using FastAPI server or Groq API.")
    parser.add_argument('--output-file', type=str, default="output.txt", help="Output file to save transcriptions.")
    parser.add_argument('--audio-file', type=str, help="Path to the audio file to transcribe.")
    parser.add_argument('--youtube-url', type=str, help="YouTube URL to download and transcribe audio.")
    parser.add_argument('--save-audio', action='store_true', default=True, help="Save the downloaded YouTube audio.")
    parser.add_argument('--engine', type=str, choices=['fast', 'groq'], default='groq', help="Transcription engine to use ('fast' or 'groq').")
    args = parser.parse_args()

    # Debugging setup
    if os.getenv('DEBUG') == '1':
        args.engine = 'fast'  # or 'groq'
        # args.engine = 'groq'  # or 'groq'
            
    audio_bytes = None
    is_microphone = False

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
        is_microphone = True
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
        process_single_transcription(args.engine, audio_bytes, args.output_file if not is_microphone else None)

if __name__ == "__main__":
    main()


# Examples of command line usafe
# python script.py 
# python script.py --youtube-url "https://www.youtube.com/watch?v=5gL9Ctwmc_g" --save-audio 
# python script.py --audio-file "gollum.mp3" 

   
