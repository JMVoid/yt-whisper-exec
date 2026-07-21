import base64
import concurrent.futures
import json
import logging
import os
import shutil
import sys
import tempfile
import time

import requests

# 将项目根目录添加到 sys.path，以确保可以从 utils 模块导入
# This allows us to import from the 'utils' module by adding the project root to the path.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import ffmpeg_split

# --- 日志记录 (Logging) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 常量定义 (Constants) ---
MAX_RETRIES = 3  # 最大重试次数 (Maximum number of retries)
RETRY_DELAY = 5  # 重试间隔秒数 (Delay between retries in seconds)


def transcribe_segment(
    segment_path: str, temp_dir: str, api_key: str, account_id: str, language: str = None
) -> dict | None:
    """
    使用 Cloudflare API 并行转录单个音频片段，包含重试逻辑。
    Transcribes a single audio segment using Cloudflare's API with retry logic.
    """
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/openai/whisper-large-v3-turbo"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        with open(segment_path, "rb") as audio_file:
            audio_data = audio_file.read()
            # 根据用户提供的参考，API期望音频字段是Base64编码的字符串。
            # According to the user's reference, the API expects the audio field to be a Base64 encoded string.
            base64_encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            payload = {
                "audio": base64_encoded_audio
            }
            if language:
                payload['language'] = language

    except IOError as e:
        logging.error(f"Error reading file {segment_path}: {e}")
        return None

    for attempt in range(MAX_RETRIES):
        try:
            logging.info(
                f"Transcribing {os.path.basename(segment_path)} (Attempt {attempt + 1}/{MAX_RETRIES})..."
            )
            response = requests.post(
                url, headers=headers, json=payload, timeout=300
            )  # 5分钟超时 (5 min timeout)
            response.raise_for_status()  # 对错误的响应 (4xx or 5xx) 抛出 HTTPError

            response_json = response.json()
            logging.info(f"Transcription successful for {os.path.basename(segment_path)}.")

            # --- 保存 JSON 文件 (Save JSON file) ---
            try:
                base_name = os.path.splitext(os.path.basename(segment_path))[0]
                json_path = os.path.join(temp_dir, f"{base_name}.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(response_json, f, ensure_ascii=False, indent=2)
                logging.info(f"Saved transcription to {json_path}")
            except Exception as e:
                logging.error(f"Error saving JSON for {os.path.basename(segment_path)}: {e}")

            return response_json
        except requests.exceptions.RequestException as e:
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
    account_id: str,
    language: str = None,
) -> list:
    """
    并发运行所有音频片段的转录任务。
    Runs transcription for all segments concurrently.
    """
    logging.info("Step 2: Starting concurrent transcription jobs...")
    results = [None] * len(segment_paths)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_index = {
            executor.submit(
                transcribe_segment, path, temp_dir, api_key, account_id, language
            ): i
            for i, path in enumerate(segment_paths)
        }

        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                if result is None:
                    # 即使一个任务失败，也允许其他任务继续，最后统一检查
                    # Even if one job fails, allow others to continue and check all at the end.
                    logging.warning(f"Transcription job failed for segment {index+1}.")
                results[index] = result
            except Exception as exc:
                logging.error(f"A critical error occurred in a transcription thread: {exc}")
                results[index] = None # 标记此任务失败 (Mark this job as failed)

    logging.info("All transcription jobs have been processed.")
    return results


def transcribe_with_cloudflare(
    audio_path: str,
    api_key: str,
    account_id: str,
    language: str = None,
    split_duration: int = 480,  # 8 minutes
) -> str | None:
    """
    分割音频文件，通过 Cloudflare 并发转录，然后拼接结果。
    Splits an audio file, transcribes segments concurrently via Cloudflare, and concatenates the results.

    Args:
        audio_path (str): 输入的音频文件路径 (Path to the input audio file).
        api_key (str): Cloudflare API 密钥 (Cloudflare API key).
        account_id (str): Cloudflare 账户 ID (Cloudflare account ID).
        language (str, optional): 音频语言 (Language of the audio). Defaults to None.
        split_duration (int, optional): 每个分割片段的时长（秒） (Duration of each split segment in seconds). Defaults to 480.

    Returns:
        str | None: 拼接后的完整转录文本，如果失败则返回 None (The concatenated full transcript, or None if it fails).
    """
    # 1. 创建一个临时目录 (Create a temporary directory)
    temp_dir = tempfile.mkdtemp()
    logging.info(f"Created temporary directory: {temp_dir}")

    try:
        # 2. 使用 utils 中的 ffmpeg_split 分割音频 (Split the audio using ffmpeg_split from utils)
        logging.info(f"Step 1: Splitting audio file: {audio_path}...")
        success, segment_paths_or_error = ffmpeg_split(
            file_path=audio_path, storage_path=temp_dir, time_len=split_duration
        )

        if not success:
            logging.error(f"Error splitting audio file: {segment_paths_or_error}")
            return None

        segment_paths = segment_paths_or_error
        logging.info(f"Audio split into {len(segment_paths)} segments.")
        for p in segment_paths:
            logging.info(f"  - Found segment: {os.path.basename(p)}")

        # 3. 对分割后的片段运行并发转录任务 (Run concurrent transcription jobs on the segments)
        transcription_results = run_transcription_jobs(
            segment_paths=segment_paths,
            temp_dir=temp_dir,
            api_key=api_key,
            account_id=account_id,
            language=language,
        )

        if any(r is None for r in transcription_results):
            logging.warning(
                "One or more transcription jobs failed. The final transcript may be incomplete."
            )

        # 4. 按顺序拼接转录结果 (Concatenate the transcription results in order)
        logging.info("Step 3: Concatenating transcription results...")
        full_transcript = []
        # 结果列表的顺序与分割文件的顺序一致
        # The order of the results list matches the order of the split files.
        for i, result in enumerate(transcription_results):
            if (
                result
                and result.get("success")
                and "result" in result
                and "text" in result["result"]
            ):
                full_transcript.append(result["result"]["text"])
            else:
                segment_name = os.path.basename(segment_paths[i])
                logging.warning(
                    f"Could not find text in result for segment {segment_name}. Skipping."
                )
                logging.warning(f"         Received data: {result}")


        final_text = " ".join(full_transcript).strip()
        logging.info("Concatenation complete.")
        return final_text

    finally:
        # 5. 清理临时目录 (Clean up the temporary directory)
        logging.info(f"Step 4: Cleaning up temporary directory: {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
            logging.info("Cleanup successful.")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
