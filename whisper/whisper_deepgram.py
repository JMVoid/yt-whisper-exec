import concurrent.futures
import concurrent.futures
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from typing import Optional, Callable
from utils.utils import ffmpeg_split

from deepgram.client import DeepgramClient

# 将项目根目录添加到 sys.path，以确保可以从 utils 模块导入
# This allows us to import from the 'utils' module by adding the project root to the path.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# --- 日志记录 (Logging) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 常量定义 (Constants) ---
MAX_RETRIES = 3  # 最大重试次数 (Maximum number of retries)
RETRY_DELAY = 5  # 重试间隔秒数 (Delay between retries in seconds)


def transcribe_segment(
    segment_path: str, temp_dir: str, api_key: str, language: str = None
) -> dict | None:
    """
    使用 Deepgram API 并行转录单个音频片段，包含重试逻辑。
    Transcribes a single audio segment using Deepgram's API with retry logic.
    """
    for attempt in range(MAX_RETRIES):
        try:
            logging.info(
                f"Transcribing {os.path.basename(segment_path)} (Attempt {attempt + 1}/{MAX_RETRIES})..."
            )
    
            # 1. 初始化 DeepgramClient
            deepgram = DeepgramClient(api_key=api_key)
            # 2. 读取音频文件
            print("segment path:", segment_path)
            with open(segment_path, "rb") as audio_file:
                buffer_data = audio_file.read()

            # 3. 配置转录选项
            options = {
                "model": "nova-2",
                "smart_format": True,
                "punctuate": True,
                "utterances": True,
            }
            if language:
                options["language"] = language
            else:
                options["detect_language"] = True

            # 4. 发送转录请求
            response = deepgram.listen.v1.media.transcribe_file(
                request=buffer_data, **options
            )

            response_json = json.loads(response.json())
            logging.info(f"Transcription successful for {os.path.basename(segment_path)}.")

            # # --- 保存 JSON 文件 (Save JSON file) ---
            try:
                base_name = os.path.splitext(os.path.basename(segment_path))[0]
                json_path = os.path.join(temp_dir, f"{base_name}.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(response_json, f, ensure_ascii=False, indent=2)
                logging.info(f"Saved transcription to {json_path}")
            except Exception as e:
                logging.error(f"Error saving JSON for {os.path.basename(segment_path)}: {e}")

            return response_json

        except Exception as e:
            logging.error(
                f"Error during transcription for {os.path.basename(segment_path)}: {e}"
            )
            if attempt < MAX_RETRIES - 1:
                logging.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logging.error(
                    f"Failed to transcribe {os.path.basename(segment_path)} after {MAX_RETRIES} attempts."
                )
                return None
    return None


def run_transcription_jobs(
    segment_paths: list,
    temp_dir: str,
    api_key: str,
    language: str = None,
    max_workers: int = 4,
) -> list:
    """
    并发运行所有音频片段的转录任务。
    Runs transcription for all segments concurrently.
    """
    logging.info(f"Step 2: Starting concurrent transcription jobs with {max_workers} workers...")
    results = [None] * len(segment_paths)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                transcribe_segment, path, temp_dir, api_key, language
            ): i
            for i, path in enumerate(segment_paths)
        }

        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                if result is None:
                    logging.warning(f"Transcription job failed for segment {index+1}.")
                results[index] = result
            except Exception as exc:
                logging.error(f"A critical error occurred in a transcription thread: {exc}")
                results[index] = None

    logging.info("All transcription jobs have been processed.")
    return results


def transcribe_with_deepgram(
    audio_path: str,
    api_key: str,
    language: str = None,
    split_duration: int = 300,  # 8 minutes
    temp_dir_path: Optional[str] = None,  # <-- 添加此参数
    max_workers: int = 4,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> str | None:
    """
    分割音频文件，通过 Deepgram 并发转录，然后拼接结果。
    Splits an audio file, transcribes segments concurrently via Deepgram, and concatenates the results.

    Args:
        audio_path (str): 输入的音频文件路径 (Path to the input audio file).
        api_key (str): Deepgram API 密钥 (Deepgram API key).
        language (str, optional): 音频语言 (Language of the audio). Defaults to None.
        split_duration (int, optional): 每个分割片段的时长（秒） (Duration of each split segment in seconds). Defaults to 480.
        temp_dir_path (Optional[str], optional): 外部提供的临时目录路径. 如果为 None, 将在内部创建. Defaults to None.
        progress_callback (Optional[Callable[[str, float], None]], optional): 进度回调函数，接收消息和进度百分比.

    Returns:
        str | None: 拼接后的完整转录文本，如果失败则返回 None (The concatenated full transcript, or None if it fails).
    """
    is_external_temp_dir = temp_dir_path is not None
    temp_dir = temp_dir_path if is_external_temp_dir else tempfile.mkdtemp()

    if is_external_temp_dir:
        logging.info(f"Using provided temporary directory: {temp_dir}")
    else:
        logging.info(f"Created temporary directory: {temp_dir}")

    try:
        if progress_callback:
            progress_callback("Splitting audio file...", 25)
            
        logging.info(f"Step 1: Splitting audio file: {audio_path}...")
        success, segment_paths_or_error = ffmpeg_split(
            file_path=audio_path, storage_path=temp_dir, time_len=split_duration
        )

        if not success:
            logging.error(f"Error splitting audio file: {segment_paths_or_error}")
            if progress_callback:
                progress_callback("Error splitting audio file", 0)
            return None

        segment_paths = segment_paths_or_error
        logging.info(f"Audio split into {len(segment_paths)} segments.")
        for p in segment_paths:
            logging.info(f"  - Found segment: {os.path.basename(p)}")
            
        if progress_callback:
            progress_callback(f"Audio split into {len(segment_paths)} segments. Starting transcription...", 30)

        # 使用新的带进度更新的转录任务函数
        transcription_results = run_transcription_jobs_with_progress(
            segment_paths=segment_paths,
            temp_dir=temp_dir,
            api_key=api_key,
            language=language,
            max_workers=max_workers,
            progress_callback=progress_callback,
            total_segments=len(segment_paths)
        )

        if any(r is None for r in transcription_results):
            logging.warning(
                "One or more transcription jobs failed. The final transcript may be incomplete."
            )

        logging.info("Step 3: Concatenating transcription results...")
        if progress_callback:
            progress_callback("Concatenating transcription results...", 90)
            
        full_transcript = []
        completed_segments = 0
        
        for i, result in enumerate(transcription_results):
            try:
                if result and result['results']['channels'][0]['alternatives'][0]['transcript']:
                    full_transcript.append(result['results']['channels'][0]['alternatives'][0]['transcript'])
                    completed_segments += 1
                    
                    # 发送进度更新
                    if progress_callback:
                        current_progress = 90 + (10 * completed_segments / len(transcription_results))
                        progress_callback(f"Completed segment {completed_segments}/{len(transcription_results)}", current_progress)
                        
                else:
                    segment_name = os.path.basename(segment_paths[i])
                    logging.warning(
                        f"Could not find transcript in result for segment {segment_name}. Skipping."
                    )
                    logging.warning(f"         Received data: {result}")
            except (KeyError, IndexError) as e:
                segment_name = os.path.basename(segment_paths[i])
                logging.warning(f"Malformed result for segment {segment_name}, error: {e}. Skipping.")
                logging.warning(f"         Received data: {result}")


        final_text = " ".join(full_transcript).strip()
        logging.info("Concatenation complete.")
        if progress_callback:
            progress_callback("Transcription complete!", 100)
        return final_text

    finally:
        if not is_external_temp_dir:
            logging.info(f"Step 4: Cleaning up internally created temporary directory: {temp_dir}")
            try:
                shutil.rmtree(temp_dir)
                logging.info("Cleanup successful.")
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")
        else:
            logging.info(f"Step 4: Skipping cleanup for externally provided temporary directory: {temp_dir}")


def run_transcription_jobs_with_progress(
    segment_paths: list,
    temp_dir: str,
    api_key: str,
    language: str = None,
    max_workers: int = 4,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    total_segments: int = 0
) -> list:
    """
    并发运行所有音频片段的转录任务，支持进度更新。
    Runs transcription for all segments concurrently with progress updates.
    """
    logging.info(f"Step 2: Starting concurrent transcription jobs with {max_workers} workers...")
    
    if progress_callback:
        progress_callback(f"Starting transcription of {total_segments} segments with {max_workers} workers...", 35)
    
    results = [None] * len(segment_paths)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                transcribe_segment, path, temp_dir, api_key, language
            ): i
            for i, path in enumerate(segment_paths)
        }

        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                if result is None:
                    logging.warning(f"Transcription job failed for segment {index+1}.")
                results[index] = result
                
                # 更新进度
                completed_count += 1
                if progress_callback:
                    current_progress = 35 + (55 * completed_count / len(segment_paths))
                    progress_callback(f"Completed {completed_count}/{len(segment_paths)} segments", current_progress)
                    
            except Exception as exc:
                logging.error(f"A critical error occurred in a transcription thread: {exc}")
                results[index] = None

    logging.info("All transcription jobs have been processed.")
    return results
