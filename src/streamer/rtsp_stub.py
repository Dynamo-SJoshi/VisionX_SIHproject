# File: src/streamer/rtsp_stub.py
import logging
from typing import Union

logger = logging.getLogger(__name__)


def start_stream_stub(video_source: Union[int, str] = 0, target_ip: str = "127.0.0.1", port: int = 8554) -> Dict_or_str: # type: ignore
    """
    Placeholder function for local RTSP/HTTP video streaming server.

    Args:
        video_source: Local camera index or source video path.
        target_ip: Target destination IP address.
        port: RTSP port number.

    Returns:
        String stream status summary.
    """
    stream_url = f"rtsp://{target_ip}:{port}/bas_live_feed"
    msg = f"[STREAMER STUB]: Initialized RTSP stream from source '{video_source}' -> {stream_url}"
    logger.info(msg)
    print(msg)
    return stream_url
