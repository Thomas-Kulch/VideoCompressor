import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog

try:
    import ffmpeg  # Attempt to import ffmpeg module
except ImportError:
    print("FFmpeg module not found. Installing FFmpeg...")
    try:
        subprocess.run(["pip", "install", "ffmpeg-python"], check=True)
        print("FFmpeg module installed. Please make sure FFmpeg is installed on your local machine and is added to your PATH. Refer to README for instructions.")
        import ffmpeg  # Reimport ffmpeg module after installation
    except subprocess.CalledProcessError:
        print("Failed to install FFmpeg module. Please install FFmpeg manually and add it to your PATH. Refer to README for instructions.")
        exit(1)


def get_video_duration(input_file: str) -> float:
    """
    Get the duration of the video in seconds.

    input_file - Path to the input video file.
    return - Duration of the video in seconds.
    """
    probe = ffmpeg.probe(input_file)
    duration = float(probe['format']['duration'])
    return duration


def compress_video(input_file: str, output_file: str, max_size_mb: float, ffmpeg_path: str):
    """
    Compress a video file to ensure its size is below max_size_mb while minimizing quality loss.

    input_file - Path to the input video file.
    output_file - Path to save the compressed video file.
    max_size_mb - Maximum allowed size for the compressed video in MB.
    ffmpeg_path - Path to the ffmpeg executable.
    """
    print("Starting compression process...")

    try:
        duration = get_video_duration(input_file)
        target_size_bytes = max_size_mb * 1024 * 1024
        max_iterations = 10  # Maximum number of bitrate adjustment iterations

        print(f"Target size: {max_size_mb} MB")
        print(f"Duration: {duration} seconds")

        # Compress video with initial bitrate estimate using two-pass encoding
        initial_bitrate = (target_size_bytes * 8) / duration  # bits per second
        initial_bitrate_kbps = initial_bitrate / 1024  # kilobits per second
        current_bitrate_kbps = initial_bitrate_kbps

        for _ in range(max_iterations):
            current_bitrate = f'{int(current_bitrate_kbps)}k'

            print(f"Adjusting bitrate to: {current_bitrate}...")

            ffmpeg.input(input_file).output(
                'temp_pass1.mp4',
                video_bitrate=current_bitrate,
                **{'pass': 1, 'preset': 'medium'}
            ).run(cmd=ffmpeg_path, capture_stderr=True)

            ffmpeg.input(input_file).output(
                output_file,
                video_bitrate=current_bitrate,
                **{'pass': 2, 'preset': 'medium'}
            ).run(overwrite_output=True, cmd=ffmpeg_path, capture_stderr=True)

            current_size_bytes = os.path.getsize(output_file)
            current_size_mb = current_size_bytes / (1024 * 1024)

            print(f"Current size: {current_size_mb} MB")

            if current_size_bytes <= target_size_bytes:
                print("Target size met.")
                break  # Exit the loop if the target size is met or slightly exceeded

            current_bitrate_kbps *= (max_size_mb / current_size_mb) * 0.95

            # Delete the temporary file before the next iteration
            if os.path.exists('temp_pass1.mp4'):
                os.remove('temp_pass1.mp4')

    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e.stderr.decode('utf-8')}")

    except Exception as ex:
        print(f"Error: {ex}")

    finally:
        # Clean up temporary file
        if os.path.exists('temp_pass1.mp4'):
            os.remove('temp_pass1.mp4')
        if os.path.exists('ffmpeg2pass-0.log'):
            os.remove('ffmpeg2pass-0.log')
        if os.path.exists('ffmpeg2pass-0.log.mbtree'):
            os.remove('ffmpeg2pass-0.log.mbtree')

    print("Compression process completed.")


def get_ffmpeg_path():
    """Return the path to the bundled ffmpeg.exe if running as a PyInstaller EXE."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        return os.path.join(getattr(sys, '_MEIPASS'), "ffmpeg.exe")
    else:
        # Running as script
        return "ffmpeg"


def process_folder(input_folder: str, output_folder: str, max_size_mb: float = 25.0, ffmpeg_path: str = get_ffmpeg_path()):
    """
    Executes the entire operation.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(input_folder):
        input_file = os.path.join(input_folder, filename)
        if os.path.isfile(input_file) and input_file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
            output_file = os.path.join(output_folder, filename)
            print(f"Compressing {filename}...")
            compress_video(input_file, output_file, max_size_mb, ffmpeg_path)
            print(f"Compressed {filename} to {output_file}")


def select_folder() -> str:
    """
    Opens file explorer to select input folder for compressing videos.
    """
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    root.destroy()
    return folder_selected



if __name__ == "__main__":
    print('Welcome to Video Compressor!')
    size = float(input('Enter the size of the video in MB: '))
    input_folder_path = select_folder()
    if input_folder_path:
        output_folder_path = os.path.join(
            input_folder_path, 'compressed_videos')
        process_folder(input_folder_path, output_folder_path, size)
    else:
        print("No folder selected. Exiting.")
