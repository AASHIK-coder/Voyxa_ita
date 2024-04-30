import soundfile as sf
import sounddevice as sd
import numpy as np
import config
import threading

def play_sound_file(file_name, volume, verbose=False):
    """
    Play a sound file at a given volume, followed by a period of silence.

    Args:
        file_name (str): The path to the sound file to be played.
        volume (float): The volume at which to play the sound file.
        verbose (bool, optional): Whether to print verbose output. Defaults to False.

    Raises:
        FileNotFoundError: If the sound file does not exist.
        Exception: If there is an error reading or playing the sound file.
    """
    try:
        with sf.SoundFile(file_name, 'r') as sound_file:
            data = sound_file.read(dtype='int16')
            silence = np.zeros((sound_file.samplerate, data.shape[1]), dtype='int16')
            sd.play(np.concatenate((data * volume, silence)), sound_file.samplerate)
            sd.wait()
    except FileNotFoundError as e:
        if verbose:
            print(f"The sound file {file_name} was not found.")
        raise FileNotFoundError(f"The sound file {file_name} was not found.") from e
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"An error occurred while playing the sound file: {e}")
        raise Exception(f"An error occurred while playing the sound file: {e}") from e

def play_sound_FX(name, volume=1.0, verbose=False):
    """
    Play a sound effect with a specified name and volume.
    This function adjusts the volume based on a base volume setting and plays the sound asynchronously in a separate thread.

    Args:
        name (str): The name of the sound effect to be played.
        volume (float, optional): The volume at which to play the sound effect. Defaults to 1.0.
        verbose (bool, optional): Whether to print verbose output. Defaults to False.
    """
    try:
        volume *= config.BASE_VOLUME
        sound_file_name = f"sounds/recording-{name}.mp3"
        
        if verbose:
            print(f"Playing sound FX: {sound_file_name}")
        
        # Create a thread to play the sound asynchronously
        sound_thread = threading.Thread(target=play_sound_file, args=(sound_file_name, volume, verbose))
        sound_thread.start()
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"An error occurred while attempting to play sound FX: {e}")