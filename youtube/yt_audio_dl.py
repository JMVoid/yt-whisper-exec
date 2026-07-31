import logging
from typing import Optional
import yt_dlp


def dl_audio(url: str, store_path: str, proxy: Optional[str] = None, cookies: Optional[str] = None):
    """
    使用 yt-dlp 下载 YouTube 视频的音频。

    参数:
        url (str): YouTube 视频 URL。
        store_path (str): 音频文件的保存目录。
        proxy (Optional[str]): 代理地址，如 "http://host:port"。默认为 None。
        cookies (Optional[str]): Chrome cookie 文件路径。如果提供，将禁用代理。

    返回:
        tuple: (bool, str | dict)
            - 成功时: (True, {"path": str, "title": str, "description": str, "video_id": str})
            - 失败时: (False, error_message: str)
    """
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{store_path}/%(id)s_audio.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
        }
        if proxy and not cookies:
            ydl_opts['proxy'] = proxy
        if cookies:
            ydl_opts['cookiefile'] = cookies

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 先提取元数据
            info = ydl.extract_info(url, download=False)
            # 执行下载
            ydl.download([url])

            out_file = f"{store_path}/{info['id']}_audio.m4a"
            logging.info(f"音频已成功下载: {out_file}")
            return True, {
                "path": out_file,
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "video_id": info.get("id", ""),
            }
    except Exception as e:
        error_msg = f"下载音频时出错: {str(e)}"
        logging.error(error_msg)
        return False, error_msg