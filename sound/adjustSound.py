from pydub import AudioSegment
track = "theme.wav"
sound = AudioSegment.from_wav(track)

quieter_sound = sound - 15

quieter_sound.export('q_' + track, format='wav')
