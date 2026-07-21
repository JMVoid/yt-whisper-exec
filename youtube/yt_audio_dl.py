import logging
from pytubefix import YouTube

def dl_audio(yt_object: YouTube, store_path: str):
    try:
        audio_stream = yt_object.streams.get_default_audio_track().get_audio_only()
        out_file = audio_stream.download(output_path=store_path, filename=f"{yt_object.video_id}_audio.m4a")
        logging.info(f"音频已成功下载: {out_file}")
        return True, out_file
    except Exception as e:
        error_msg = f"下载音频时出错: {str(e)}"
        logging.error(error_msg)
        return False, error_msg
