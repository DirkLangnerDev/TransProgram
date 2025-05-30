import pyaudio
import wave
import keyboard
import threading
import time
import pyperclip
import winsound
import whisper
import numpy as np
import tempfile
import os
import pystray
from PIL import Image
import io
from pathlib import Path
import subprocess
import sys
import sqlite3
import datetime

class VoiceMemoRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        
        # Audio-Aufnahme-Einstellungen
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 1
        self.RATE = 16000
        
        self.p = pyaudio.PyAudio()
        
        # Überprüfe, ob FFmpeg verfügbar ist
        self.check_ffmpeg()
        
        # Lade Modell und nutze GPU wenn verfügbar
        import torch
        self.model = whisper.load_model("turbo")
        if torch.cuda.is_available():
            self.model = self.model.cuda()
            print("GPU wird verwendet")
        else:
            print("CPU wird verwendet")
            
        # Initialisiere die Datenbank
        self.init_db()
            
        # Erstelle ein einfaches Icon für den Systray
        self.create_icon()
        
    def init_db(self):
        """Initialisiert die SQLite-Datenbank für die Transkript-Protokollierung."""
        # Erstelle den Datenbankordner, falls er nicht existiert
        self.db_path = Path("transcripts.db")
        
        # Verbinde zur Datenbank (wird erstellt, falls nicht vorhanden) und erstelle die Tabelle
        # Wir erstellen hier nur die Tabelle, aber verwenden keine dauerhafte Verbindung
        # um Thread-Probleme zu vermeiden
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Erstelle die Tabelle, falls sie nicht existiert
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            transcript TEXT NOT NULL
        )
        ''')
        conn.commit()
        conn.close()
        print(f"Datenbank initialisiert: {self.db_path}")
        
    def log_message(self, transcript):
        """Speichert ein transkribiertes Memo in der Datenbank."""
        # Erstelle für jede Operation eine neue Verbindung, um Thread-Sicherheit zu gewährleisten
        try:
            timestamp = datetime.datetime.now().isoformat()
            
            # Neue Verbindung für diese Operation
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO messages (timestamp, transcript) VALUES (?, ?)",
                (timestamp, transcript)
            )
            conn.commit()
            conn.close()
            print(f"Memo gespeichert: {timestamp[:19]}")
        except Exception as e:
            print(f"Fehler beim Speichern des Memos: {e}")
    
    def check_ffmpeg(self):
        """Überprüft, ob FFmpeg verfügbar ist und gibt Hinweise, wenn nicht."""
        try:
            # Versuche, FFmpeg zu finden
            subprocess.run(
                ["ffmpeg", "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )
            print("FFmpeg gefunden")
        except (subprocess.SubprocessError, FileNotFoundError):
            print("FEHLER: FFmpeg nicht gefunden!")
            print("Bitte installieren Sie FFmpeg und stellen Sie sicher, dass es im PATH ist.")
            print("Download: https://ffmpeg.org/download.html")
            print("Oder installieren Sie es mit: choco install ffmpeg (wenn Chocolatey installiert ist)")
            print("Nach der Installation starten Sie das Programm neu.")
            
            # Zeige Meldung und beende das Programm
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "FFmpeg nicht gefunden", 
                "FFmpeg wird für die Audioverarbeitung benötigt, wurde aber nicht gefunden.\n\n"
                "Bitte installieren Sie FFmpeg und stellen Sie sicher, dass es im PATH ist.\n"
                "Download: https://ffmpeg.org/download.html\n\n"
                "Nach der Installation starten Sie das Programm neu."
            )
            sys.exit(1)
    
    def create_icon(self):
        # Erstelle ein einfaches rotes Quadrat als Icon
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='green')
        self.icon = pystray.Icon(
            "voice_memo",
            image,
            "Voice Memo (Strg+Alt+R)",
            menu=pystray.Menu(
                pystray.MenuItem("Beenden", self.stop_application)
            )
        )
        
    def start_recording(self):
        self.recording = True
        self.frames = []
        
        # Öffne den Audio-Stream
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        # Ändere Icon-Farbe zu grün während der Aufnahme
        self.update_icon_color('red')
        
        # Signalton für Start der Aufnahme (700 Hz für 100ms - sanfter, höherer Ton)
        winsound.Beep(700, 100)
        
        # Aufnahme-Schleife
        while self.recording:
            data = self.stream.read(self.CHUNK)
            self.frames.append(data)
            
    def stop_recording(self):
        self.recording = False
        
        # Signalton für Ende der Aufnahme (500 Hz für 100ms - sanfter, tieferer Ton)
        winsound.Beep(500, 100)
        
        # Ändere Icon-Farbe zurück zu rot
        self.update_icon_color('red')
        
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
            
        # Speichere die Aufnahme temporär
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_filename = temp_wav.name
            
            wf = wave.open(temp_filename, 'wb')
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            
            # Konvertiere Float32 zu Int16 für WAV-Datei
            audio_data = np.frombuffer(b''.join(self.frames), dtype=np.float32)
            audio_data = (audio_data * 32767).astype(np.int16)
            wf.writeframes(audio_data.tobytes())
            wf.close()
        
        # Transkribiere mit Whisper (Deutsch)
        result = self.model.transcribe(temp_filename, language="de")
        transcript = result["text"]
        
        # Speichere in der Datenbank
        self.log_message(transcript)
        
        # Kopiere in die Zwischenablage
        pyperclip.copy(transcript)
        
        # Signalton für erfolgreiche Transkription (600 Hz für 100ms - mittlerer, erfolgreicher Ton)
        winsound.Beep(600, 100)
        
        # Lösche temporäre Datei
        os.unlink(temp_filename)
        
    def update_icon_color(self, color):
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color=color)
        self.icon.icon = image
        
    def stop_application(self):
        if self.recording:
            self.stop_recording()
        keyboard.unhook_all()
        self.p.terminate()
        self.icon.stop()

def main():
    recorder = VoiceMemoRecorder()
    recording_thread = None
    
    def start_stop_recording():
        nonlocal recording_thread
        
        if not recorder.recording:
            # Starte Aufnahme in neuem Thread
            recording_thread = threading.Thread(target=recorder.start_recording)
            recording_thread.start()
        else:
            # Stoppe Aufnahme
            recorder.stop_recording()
            if recording_thread:
                recording_thread.join()
    
    # Registriere Hotkey (Strg + Alt + R)
    keyboard.add_hotkey('ctrl+alt+r', start_stop_recording)
    
    # Starte Icon im Systray
    recorder.icon.run()

if __name__ == "__main__":
    main()
