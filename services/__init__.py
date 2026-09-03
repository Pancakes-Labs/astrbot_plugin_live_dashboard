"""services 子包：放置请求、渲染与业务编排逻辑。"""

from .api_client import (
    ApiClient,
    ApiError,
    AuthenticationError,
    HttpApiError,
    InvalidResponseError,
    NetworkApiError,
    TimeoutApiError,
    make_client_from_config,
)
from .base_service import BaseService
from .dashboard_service import DashboardService
from .friend_service import FriendService
from .health_service import HealthService
from .system_status_service import SystemStatusService
from .telemetry_service import TelemetryManager
from .telemetry_utils import track_error_safely, track_feature_safely
from .timeline_service import TimelineService

__all__ = [
    "ApiClient",
    "ApiError",
    "AuthenticationError",
    "HttpApiError",
    "InvalidResponseError",
    "NetworkApiError",
    "TimeoutApiError",
    "make_client_from_config",
    "BaseService",
    "DashboardService",
    "TimelineService",
    "HealthService",
    "FriendService",
    "SystemStatusService",
    "TelemetryManager",
    "track_feature_safely",
    "track_error_safely",
]
