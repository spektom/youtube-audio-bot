import logging
import os
import subprocess


def get_duration(audio_file):
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_file,
        ],
        capture_output=True,
    )
    return float(p.stdout) if p.returncode == 0 else 0


def convert_to_mp3(input_file, offset, size_limit, output_file):
    logging.info(f"processing '{input_file}', offset={offset}")
    # Convert to MP3 and normalize voice volume
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "error",
            "-i",
            input_file,
            "-af",
            f"compand=0|0:1|1:-90/-900|-70/-70|-30/-9|0/-3:6:0:0:0",
            "-acodec",
            "mp3",
            "-ss",
            str(offset),
            "-fs",
            str(size_limit),
            "-y",
            output_file,
        ]
    )


def split_convert_to_mp3(audio_file, duration_secs, max_size_limit):
    if os.path.getsize(audio_file) < max_size_limit:
        return [(audio_file, duration_secs)]
    parts = []
    part_idx = 0
    offset = 0
    logging.info(f"splitting '{audio_file}', duration={duration_secs}")
    while offset < duration_secs:
        part_file = f"{audio_file}-{part_idx}.mp3"
        if not os.path.exists(part_file):
            convert_to_mp3(audio_file, offset, max_size_limit, part_file)
        part_len = get_duration(part_file)
        if part_len == 0:
            os.remove(part_file)
            break
        logging.info(f"created '{part_file}', duration={part_len}")
        parts.append((part_file, part_len))
        offset += part_len
        part_idx += 1
    return parts
