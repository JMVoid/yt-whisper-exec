import argparse
import os
import asyncio
import json
import logging
import tempfile
from typing import Optional, Dict, Any

from youtube.yt_audio_dl import dl_audio
from whisper.whisper_deepgram import transcribe_with_deepgram
from utils.constant import MAX_WORKERS_NUMBER

from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载环境变量
load_dotenv()

# 获取环境变量
yt_dl_proxy: Optional[str] = os.getenv("YT_DL_PROXY")
whisper_provider: Optional[str] = os.getenv("WHISPER_PROVIDER")
whisper_api_key: Optional[str] = os.getenv("WHISPER_API_KEY")

SuccessResponse = Dict[str, Any]
ErrorResponse = Dict[str, str]


def check_environment():
    """Check required environment variables and log warnings"""
    if whisper_provider and whisper_api_key:
        logging.info(f"Transcription provider configured: {whisper_provider}")
    elif whisper_provider or whisper_api_key:
        logging.warning("Incomplete transcription configuration: both WHISPER_PROVIDER and WHISPER_API_KEY are required")
    
    if yt_dl_proxy:
        logging.info(f"Proxy configured: {yt_dl_proxy}")
    else:
        warning_msg = (
            "No proxy configuration detected. "
            "When running this tool, if you encounter 'detect Bot' errors, "
            "you will need to purchase and set up the appropriate proxy configuration."
        )
        logging.warning(warning_msg)


class Context:
    """Simple context simulation class"""
    async def info(self, msg: str):
        logging.info(msg)
    
    async def error(self, msg: str):
        logging.error(msg)
    
    async def debug(self, msg: str):
        logging.debug(msg)
    
    async def report_progress(self, current: int, total: int, msg: str):
        logging.info(f"Progress: {current}/{total} - {msg}")

async def audio_transcribe_with_id(url: str, language: Optional[str] = None, cookies: Optional[str] = None) -> Dict[str, Any]:
    """音频转录核心逻辑"""
    # Check environment variables first
    if not whisper_provider or not whisper_api_key:
        error_response: ErrorResponse = {
            "status": "error",
            "reason": "Transcription is not available: WHISPER_PROVIDER and WHISPER_API_KEY environment variables must be set"
        }
        logging.error("Whisper Provider and API Key must be set")
        # Create ctx only for this early return path
        ctx = Context()
        await ctx.error("Transcription is not available: WHISPER_PROVIDER and WHISPER_API_KEY environment variables must be set")
        return error_response
    
    # Initialize context for the rest of the function
    ctx = Context()
    
    original: str = whisper_provider

    # 定义支持的语言代码集合
    supported_languages = {
        "en", "zh", "es", "hi", "ar", "pt", "ru", "ja", "fr", "de", "ko", "it",
        "tr", "nl", "pl", "vi", "th", "id", "ms", "fa", "ur", "bn", "he",
        "fil", "sv", "el", "cs", "hu", "da", "no", "fi", "ro", "uk", "sr"
    }

    # 验证提供的语言代码
    if language and language not in supported_languages:
        logging.warning(f"Invalid language code '{language}' provided. Falling back to auto-detection.")
        language = None  # 设置为None以触发自动检测

    transcribe_fn = None
    match whisper_provider.lower():
        case "deepgram":
            transcribe_fn = transcribe_with_deepgram
        case "cloudflare":
            # 占位符
            pass
        case "groq":
            # 占位符
            pass
        case _:
            logging.error(f"provider {original} must be one of deepgram, cloudflare, groq")
            error_response: ErrorResponse = {
                "status": "error",
                "reason": "The provider must one of deepgram, cloudflare, groq"
            }
            await ctx.error("The provider must one of deepgram, cloudflare, groq")
            return error_response

    if transcribe_fn is None:
        error_msg = f"Transcription provider '{whisper_provider}' is not implemented yet."
        await ctx.error(error_msg)
        return {
            "status": "failure",
            "reason": error_msg
        }

    # 心跳任务保持连接
    async def heartbeat_task(stop_event):
        while not stop_event.is_set():
            try:
                await ctx.debug("Transcription in progress... keeping connection alive")
                await asyncio.sleep(30)  # 每30秒发送一次心跳
            except Exception as e:
                logging.warning(f"Heartbeat task error: {e}")
                break

    stop_heartbeat = asyncio.Event()
    heartbeat_task_handle = asyncio.create_task(heartbeat_task(stop_heartbeat))

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 初始进度更新
            await ctx.info(f"Starting audio transcription for {url}")
            await ctx.report_progress(5, 100, "Initializing...")
            
            logging.info(f"Created temporary directory for audio processing: {temp_dir}")
            
            # 下载音频阶段
            await ctx.info("Downloading audio from YouTube...")
            await ctx.report_progress(10, 100, "Downloading audio")
            
            logging.info(f"Downloading audio from {url} to {temp_dir}")
            success, result_or_error = dl_audio(url, temp_dir, yt_dl_proxy, cookies)

            if not success:
                error_msg = f"Failed to download audio: {result_or_error}"
                logging.error(error_msg)
                await ctx.error(error_msg)
                stop_heartbeat.set()
                await heartbeat_task_handle
                return {"status": "failure", "reason": error_msg}

            audio_file_path = result_or_error["path"]
            video_title = result_or_error["title"]
            video_description = result_or_error["description"]

            # 转录阶段
            await ctx.info("Audio downloaded successfully. Starting transcription...")
            await ctx.report_progress(30, 100, "Processing audio file")
            
            logging.info(f"Starting transcription for {audio_file_path}")
            
            # 创建进度回调
            def create_progress_callback():
                async def _progress_update(msg, pct):
                    try:
                        await ctx.info(msg)
                        await ctx.report_progress(pct, 100, msg)
                    except Exception as e:
                        logging.warning(f"Progress update error: {e}")
                
                return _progress_update
            
            # 创建同步回调
            progress_callback = create_progress_callback()
            
            # 使用队列处理进度更新
            import queue
            progress_queue = queue.Queue()
            
            def sync_progress_callback(msg, pct):
                progress_queue.put((msg, pct))
            
            # 在线程中运行转录
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None,
                transcribe_fn,
                audio_file_path,               # audio_path
                whisper_api_key,                # api_key
                language,                       # language
                480,                            # split_duration
                temp_dir,                       # temp_dir_path
                MAX_WORKERS_NUMBER,             # max_workers
                sync_progress_callback          # progress_callback
            )
            
            # 处理进度队列
            while not progress_queue.empty():
                try:
                    msg, pct = progress_queue.get_nowait()
                    await ctx.info(msg)
                    await ctx.report_progress(pct, 100, msg)
                except queue.Empty:
                    break

            if transcript is None:
                await ctx.error("Transcription process failed.")
                stop_heartbeat.set()
                await heartbeat_task_handle
                return {"status": "failure", "reason": "Transcription process failed."}

            await ctx.info("Transcription completed successfully!")
            await ctx.report_progress(100, 100, "Transcription complete")
            
            # 停止心跳任务
            stop_heartbeat.set()
            await heartbeat_task_handle
            
            return {
                "status": "success",
                "title": video_title,
                "description": video_description,
                "transcript": transcript
            }

        except Exception as e:
            error_msg = f"An error occurred during audio processing for URL {url}: {e}"
            logging.error(error_msg, exc_info=True)
            await ctx.error(error_msg)
            stop_heartbeat.set()
            await heartbeat_task_handle
            return {"status": "failure", "reason": error_msg}

def main():
    """CLI entry point"""
    # Initialize environment check
    check_environment()
    
    parser = argparse.ArgumentParser(description='YouTube Audio Transcription Tool')
    # Main arguments (transcribe is the only function)
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--lang', help='Language code for transcription (optional, auto-detect if not specified)')
    parser.add_argument('--cookies', help='Path to Chrome cookies file for YouTube authentication (disables proxy when used)')
    parser.add_argument('-o', '--output', help='Output file path for transcription result (outputs to stdout if not specified)')
    
    args = parser.parse_args()
    
    # Execute transcription
    result = asyncio.run(audio_transcribe_with_id(args.url, args.lang, args.cookies))
    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        logging.info(f"Result written to {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    main()
