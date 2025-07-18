import time
from collections import defaultdict
import threading

class MetricsCollector:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def initialize(self):
        if self._initialized:
            return
        self.http_request_total = defaultdict(int)
        self.http_request_duration_seconds_sum = defaultdict(float)
        self.http_request_duration_seconds_count = defaultdict(int)
        
        self.model_cache_hits_total = defaultdict(int)
        self.model_cache_misses_total = defaultdict(int)
        self.model_cache_evictions_total = defaultdict(int)

        self.webhook_deliveries_total = defaultdict(int)
        self.webhook_successful_deliveries_total = defaultdict(int)
        self.webhook_failed_deliveries_total = defaultdict(int)
        self.webhook_retries_total = defaultdict(int)

        self._initialized = True

    def observe_http_request(self, endpoint: str, duration: float):
        self.http_request_total[endpoint] += 1
        self.http_request_duration_seconds_sum[endpoint] += duration
        self.http_request_duration_seconds_count[endpoint] += 1

    def increment_cache_hit(self, model_id: str):
        self.model_cache_hits_total[model_id] += 1
    
    def increment_cache_miss(self, model_id: str):
        self.model_cache_misses_total[model_id] += 1

    def increment_cache_eviction(self, model_id: str):
        self.model_cache_evictions_total[model_id] += 1

    def increment_webhook_delivery_attempt(self, webhook_url: str):
        self.webhook_deliveries_total[webhook_url] += 1

    def increment_webhook_success(self, webhook_url: str):
        self.webhook_successful_deliveries_total[webhook_url] += 1

    def increment_webhook_failure(self, webhook_url: str):
        self.webhook_failed_deliveries_total[webhook_url] += 1
    
    def increment_webhook_retry(self, webhook_url: str):
        self.webhook_retries_total[webhook_url] += 1

    def get_metrics_text(self) -> str:
        metrics = []

        for endpoint, count in self.http_request_total.items():
            safe_endpoint = endpoint.replace("/", "_").replace(".", "").replace("-", "_").strip('_')
            metrics.append(f'# HELP http_requests_total Total number of HTTP requests.')
            metrics.append(f'# TYPE http_requests_total counter')
            metrics.append(f'http_requests_total{{endpoint="{endpoint}"}} {count}')

        for endpoint, count in self.http_request_duration_seconds_count.items():
            if count > 0:
                avg_latency = self.http_request_duration_seconds_sum[endpoint] / count
                safe_endpoint = endpoint.replace("/", "_").replace(".", "").replace("-", "_").strip('_')
                metrics.append(f'# HELP http_request_duration_seconds_average Average HTTP request duration in seconds.')
                metrics.append(f'# TYPE http_request_duration_seconds_average gauge')
                metrics.append(f'http_request_duration_seconds_average{{endpoint="{endpoint}"}} {avg_latency}')
                
                metrics.append(f'# HELP http_request_duration_seconds_count Total count of HTTP request durations.')
                metrics.append(f'# TYPE http_request_duration_seconds_count counter')
                metrics.append(f'http_request_duration_seconds_count{{endpoint="{endpoint}"}} {count}')

        for model_id, count in self.model_cache_hits_total.items():
            safe_model_id = model_id.replace("-", "_")
            metrics.append(f'# HELP model_cache_hits_total Total cache hits for model {model_id}.')
            metrics.append(f'# TYPE model_cache_hits_total counter')
            metrics.append(f'model_cache_hits_total{{model_id="{model_id}"}} {count}')
        for model_id, count in self.model_cache_misses_total.items():
            safe_model_id = model_id.replace("-", "_")
            metrics.append(f'# HELP model_cache_misses_total Total cache misses for model {model_id}.')
            metrics.append(f'# TYPE model_cache_misses_total counter')
            metrics.append(f'model_cache_misses_total{{model_id="{model_id}"}} {count}')
        for model_id, count in self.model_cache_evictions_total.items():
            safe_model_id = model_id.replace("-", "_")
            metrics.append(f'# HELP model_cache_evictions_total Total cache evictions for model {model_id}.')
            metrics.append(f'# TYPE model_cache_evictions_total counter')
            metrics.append(f'model_cache_evictions_total{{model_id="{model_id}"}} {count}')
        
        for url, count in self.webhook_deliveries_total.items():
            safe_url = url.replace("/", "_").replace(":", "_").replace(".", "_").replace("-", "_").strip('_')
            metrics.append(f'# HELP webhook_deliveries_total Total webhook delivery attempts.')
            metrics.append(f'# TYPE webhook_deliveries_total counter')
            metrics.append(f'webhook_deliveries_total{{url="{url}"}} {count}')
        for url, count in self.webhook_successful_deliveries_total.items():
            safe_url = url.replace("/", "_").replace(":", "_").replace(".", "_").replace("-", "_").strip('_')
            metrics.append(f'# HELP webhook_successful_deliveries_total Total successful webhook deliveries (final attempt).')
            metrics.append(f'# TYPE webhook_successful_deliveries_total counter')
            metrics.append(f'webhook_successful_deliveries_total{{url="{url}"}} {count}')
        for url, count in self.webhook_failed_deliveries_total.items():
            safe_url = url.replace("/", "_").replace(":", "_").replace(".", "_").replace("-", "_").strip('_')
            metrics.append(f'# HELP webhook_failed_deliveries_total Total failed webhook deliveries (final attempt after all retries).')
            metrics.append(f'# TYPE webhook_failed_deliveries_total counter')
            metrics.append(f'webhook_failed_deliveries_total{{url="{url}"}} {count}')
        for url, count in self.webhook_retries_total.items():
            safe_url = url.replace("/", "_").replace(":", "_").replace(".", "_").replace("-", "_").strip('_')
            metrics.append(f'# HELP webhook_retries_total Total webhook retries attempted.')
            metrics.append(f'# TYPE webhook_retries_total counter')
            metrics.append(f'webhook_retries_total{{url="{url}"}} {count}')

        metrics.append(f'# HELP last_metrics_update_timestamp Current Unix timestamp when metrics were last updated.')
        metrics.append(f'# TYPE last_metrics_update_timestamp gauge')
        metrics.append(f'last_metrics_update_timestamp {time.time()}')

        return '\n'.join(metrics)

    def get_metrics_json(self) -> Dict[str, Any]:
        metrics = {
            "http_requests": {
                "total": dict(self.http_request_total),
                "durations": {}
            },
            "model_cache": {
                "hits_total": dict(self.model_cache_hits_total),
                "misses_total": dict(self.model_cache_misses_total),
                "evictions_total": dict(self.model_cache_evictions_total)
            },
            "webhooks": {
                "deliveries_total": dict(self.webhook_deliveries_total),
                "successful_deliveries_total": dict(self.webhook_successful_deliveries_total),
                "failed_deliveries_total": dict(self.webhook_failed_deliveries_total),
                "retries_total": dict(self.webhook_retries_total),
            },
            "timestamp": time.time()
        }
        for endpoint, count in self.http_request_duration_seconds_count.items():
            if count > 0:
                metrics["http_requests"]["durations"][endpoint] = {
                    "sum": self.http_request_duration_seconds_sum[endpoint],
                    "count": count,
                    "average_latency": self.http_request_duration_seconds_sum[endpoint] / count
                }
            else:
                 metrics["http_requests"]["durations"][endpoint] = {
                    "sum": 0,
                    "count": 0,
                    "average_latency": 0
                }
        return metrics

metrics_collector = MetricsCollector()
metrics_collector.initialize()
