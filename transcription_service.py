import os
import subprocess
import tempfile
from pathlib import Path
import google.generativeai as genai
from openai import OpenAI

class TranscriptionService:
    """Handle video transcription with Gemini and OpenAI"""
    
    def extract_audio(self, video_path):
        """Extract audio from video file using ffmpeg"""
        # Create temporary audio file
        audio_path = video_path.rsplit('.', 1)[0] + '_audio.mp3'
        
        try:
            # Use ffmpeg to extract audio
            subprocess.run([
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'libmp3lame',
                '-ar', '44100',  # Sample rate
                '-ac', '2',  # Stereo
                '-b:a', '192k',  # Bitrate
                audio_path
            ], check=True, capture_output=True)
            
            return audio_path
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to extract audio: {e.stderr.decode()}")
    
    def transcribe(self, audio_path, provider, api_key):
        """Transcribe audio using specified provider"""
        if provider == 'gemini':
            return self._transcribe_gemini(audio_path, api_key)
        elif provider == 'openai':
            return self._transcribe_openai(audio_path, api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _transcribe_gemini(self, audio_path, api_key):
        """Transcribe using Google Gemini API with speaker diarization"""
        try:
            genai.configure(api_key=api_key)
            
            # Upload audio file
            audio_file = genai.upload_file(audio_path)
            
            # Use Gemini model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = """Please transcribe this audio file with the following requirements:

1. SPEAKER IDENTIFICATION: If multiple speakers are present, identify them as "Speaker 1:", "Speaker 2:", etc. at the start of each speaking turn.

2. FORMATTING:
   - Each new speaker's dialogue should start on a new line
   - Use proper punctuation and capitalization
   - Format as natural conversation flow
   - Add paragraph breaks for topic changes

3. CONTENT CLEANING:
   - Remove filler words (um, uh, like, you know, etc.) unless they're essential to meaning
   - Remove repeated words or false starts
   - Remove profanity and slurs while maintaining the message
   - Clean up stuttering and verbal tics
   - Keep the actual conversation content intact - don't summarize or change meaning

4. OUTPUT FORMAT:
   If single speaker: Just provide the clean transcript
   If multiple speakers: Format as:
   Speaker 1: [their dialogue]
   Speaker 2: [their dialogue]
   Speaker 1: [continues...]

Provide only the transcription, no additional commentary."""
            
            response = model.generate_content([prompt, audio_file])
            
            # Delete uploaded file
            genai.delete_file(audio_file.name)
            
            return response.text
        except Exception as e:
            raise Exception(f"Gemini transcription failed: {str(e)}")
    
    def _transcribe_openai(self, audio_path, api_key):
        """Transcribe using OpenAI Whisper API with post-processing"""
        try:
            client = OpenAI(api_key=api_key)
            
            # Check file size (OpenAI has 25MB limit)
            file_size = os.path.getsize(audio_path)
            if file_size > 25 * 1024 * 1024:
                # Split audio file if too large
                raw_transcript = self._transcribe_openai_chunked(audio_path, client)
            else:
                with open(audio_path, 'rb') as audio_file:
                    raw_transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
            
            # Post-process with GPT for speaker diarization and cleanup
            return self._enhance_transcript_with_gpt(raw_transcript, client)
        except Exception as e:
            raise Exception(f"OpenAI transcription failed: {str(e)}")
    
    def _enhance_transcript_with_gpt(self, raw_transcript, client):
        """Use GPT to enhance transcript with speaker diarization and cleanup"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a transcript editor. Your task is to:

1. SPEAKER IDENTIFICATION: Analyze the conversation and identify different speakers. Label them as "Speaker 1:", "Speaker 2:", etc.
2. FORMATTING: Format the transcript with each speaker on a new line with natural conversation flow.
3. CONTENT CLEANING:
   - Remove filler words (um, uh, like, you know) unless essential
   - Remove repeated words and false starts
   - Replace profanity and slurs with [censored] while keeping meaning
   - Fix stuttering and verbal tics
   - Keep the actual content and meaning intact - don't summarize

OUTPUT FORMAT:
If single speaker: Clean transcript with paragraphs
If multiple speakers:
Speaker 1: [dialogue]
Speaker 2: [dialogue]

Provide ONLY the enhanced transcript, no explanations."""
                    },
                    {
                        "role": "user",
                        "content": f"Please enhance this transcript:\n\n{raw_transcript}"
                    }
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
        except Exception as e:
            # If GPT enhancement fails, return raw transcript
            print(f"GPT enhancement failed: {e}")
            return raw_transcript
    
    def _transcribe_openai_chunked(self, audio_path, client):
        """Transcribe large audio files in chunks"""
        chunk_duration = 600  # 10 minutes per chunk
        transcriptions = []
        
        # Get audio duration
        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ], capture_output=True, text=True)
        
        duration = float(result.stdout.strip())
        
        # Split and transcribe chunks
        temp_dir = tempfile.mkdtemp()
        try:
            num_chunks = int(duration / chunk_duration) + 1
            
            for i in range(num_chunks):
                start_time = i * chunk_duration
                chunk_path = os.path.join(temp_dir, f'chunk_{i}.mp3')
                
                # Extract chunk
                subprocess.run([
                    'ffmpeg',
                    '-i', audio_path,
                    '-ss', str(start_time),
                    '-t', str(chunk_duration),
                    '-acodec', 'copy',
                    chunk_path
                ], check=True, capture_output=True)
                
                # Transcribe chunk
                with open(chunk_path, 'rb') as chunk_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=chunk_file,
                        response_format="text"
                    )
                    transcriptions.append(transcript)
                
                os.remove(chunk_path)
            
            return ' '.join(transcriptions)
        finally:
            # Cleanup temp directory
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
