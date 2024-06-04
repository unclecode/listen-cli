# 🎤 Listen-Cli: Super-Fast Whisper Server on Colab or Groq

## Set Up Your Own Super-Fast Whisper Server on Colab! 🚀

In this repo, I show you how to set up your own open source whisper server, especially text models, running on Colab and use it everywhere!

Also, I made this handy script that allows you to transcribe audio from various sources including microphone input, audio files, and YouTube videos. 🌟

## 🎥 Example: The Hunt for Gollum

With the exciting news of the new Lord of the Rings trilogy coming in December 2026, let's use an example from "The Hunt for Gollum": [Watch on YouTube](https://www.youtube.com/watch?v=5gL9Ctwmc_g) 📺

## 🎥 Video Tutorial

For a detailed explanation, check out the video tutorial here: [YouTube Video](https://youtu.be/SrgJN7jOxoY). In this video, I walk you through the process of setting up the transcription server and using both the open-source and Groq methods.

## 🚀 Features

- **Microphone Mode**: Record and transcribe audio directly from your microphone.
- **Audio File Mode**: Transcribe audio files from your local machine.
- **YouTube URL Mode**: Download and transcribe audio from YouTube videos.
- **Save YouTube Audio**: Optionally save the downloaded YouTube audio as an MP3 file.

## 🎤 Speech-to-Text Engine

You have two options for the speech-to-text engine:

- **Groq**: A high-speed transcription service. You need to create a free account to use this service. Set the API token in your environment variables and call it "GROQ_API_TOKEN". Try it here https://console.groq.com/ 🚀
- **Fast-Whisper**: An open-source model that you can run on your own server. I provide a Jupyter notebook that shows you how to set up the server on Google Colab. 🌟

## 🧑‍💻 Launch Your Own Transcription Server

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1qYmdj6jYVcffO8IwGFSLjslg16YFQsYG#scrollTo=D7hEAnb2fqwN)

You can also launch your own high-quality transcription server using the open-source `fast-whisper` model. Check out the Jupyter notebook provided in this repository for a step-by-step guide on how to do this.

In the notebook, I demonstrate how to run the server in Google Colab and use ngrok to create a public URL for your server, allowing you to use it in your application.

## 📦 Installation

Make sure you have the required packages:

```
pip install pyaudio pytube pydub requests colorama groq
```

You may also need `ffmpeg` for audio conversions:

```
sudo apt-get install ffmpeg
```

## 📦 CLI Installation

You can install the `listen-cli` library directly from the repository using pip:

```
pip install git+https://github.com/unclecode/listen-cli.git
```

## 🔧 Usage

### CLI Usage

After installing, you can use the `listen` command in your terminal:

### 🎤 Microphone Mode

```
listen
```

### 📁 Audio File Mode

```
listen --audio-file path/to/your/audiofile.wav --engine fast
listen --audio-file path/to/your/audiofile.wav --engine groq
```

### 📺 YouTube URL Mode

```
listen --youtube-url "https://www.youtube.com/watch?v=5gL9Ctwmc_g" --engine fast
listen --youtube-url "https://www.youtube.com/watch?v=5gL9Ctwmc_g" --engine groq
```

To save the downloaded audio using the YouTube video's title:

```
listen --youtube-url "https://www.youtube.com/watch?v=5gL9Ctwmc_g" --engine fast --save-audio
```

## 📜 Script Usage

You can still use the script directly:

```
python script.py --help
```

### 🎤 Microphone Mode

```
python script.py
```

### 📁 Audio File Mode

```
python script.py --audio-file path/to/your/audiofile.wav --engine fast
python script.py --audio-file path/to/your/audiofile.wav --engine groq
```

### 📺 YouTube URL Mode

```
python script.py --youtube-url "https://www.youtube.com/watch?v=5gL9Ctwmc_g" --engine fast
python script.py --youtube-url "https://www.youtube.com/watch?v=5gL9Ctwmc_g" --engine groq
```

To save the downloaded audio using the YouTube video's title:

```
python script.py --youtube-url "https://www.youtube.com/watch?v=5gL9Ctwmc_g" --engine fast --save-audio
```

### Steps:

1. **Run the Notebook**: Open the Jupyter notebook and run the cells to launch the server.
2. **Set Up ngrok**: Use ngrok to create a public URL for your server.
3. **Use the URL**: Integrate the URL into your application to access the transcription service.

This method allows you to have your own speech-to-text generator for free! 🎉

## 🗣️ Using Groq for Fast Transcription

For a faster transcription service, you can use Groq's API. They provide a high-speed service which you can integrate into your application. Refer to the script for details on how to set up and use Groq.

## 📣 Contribute

I love contributions! Feel free to fork this project, submit pull requests, and share your improvements. Let's make this tool even better together! 🛠️

## 🌟 Star the Project

If you found this project useful, please give it a star ⭐ on GitHub!

## 🐦 Follow Me

Stay updated and follow me on X (formerly Twitter): [@unclecode](https://x.com/unclecode) 🐦

---

Happy transcribing! 🎧✨
