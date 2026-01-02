"""
시스템 리소스 체크 모듈
CPU, 메모리, 디스크 사용률을 확인합니다.
"""

import time
import psutil
from typing import Dict, Any, List
from .base import BaseChecker, CheckResult


class ResourceChecker(BaseChecker):
    """시스템 리소스를 체크하는 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__('resources', config)
        self.cpu_config = config.get('cpu', {})
        self.memory_config = config.get('memory', {})
        self.disk_config = config.get('disk', {})
        self.logger.debug(f"리소스 체커 초기화")
    
    def check(self) -> CheckResult:
        start_time = time.time()
        self.logger.debug("리소스 체크 시작")
        results = {}
        overall_ok = True
        
        if self.cpu_config.get('enabled', False):
            cpu_result = self._check_cpu()
            results['cpu'] = cpu_result
            if cpu_result['status'] == 'DOWN':
                overall_ok = False
        
        if self.memory_config.get('enabled', True):
            memory_result = self._check_memory()
            results['memory'] = memory_result
            if memory_result['status'] == 'DOWN':
                overall_ok = False
        
        if self.disk_config.get('enabled', True):
            disk_result = self._check_disk()
            results['disk'] = disk_result
            if disk_result['status'] == 'DOWN':
                overall_ok = False
        
        overall_status = 'UP' if overall_ok else 'DOWN'
        message = "All resources within thresholds" if overall_ok else "Some resources exceeded thresholds"
        duration_ms = (time.time() - start_time) * 1000
        
        if overall_ok:
            self.logger.debug(f"✅ 리소스 체크 성공")
        else:
            self.logger.warning(f"⚠️  리소스 체크 실패")
        
        return self._create_result(status=overall_status, message=message, details=results, duration_ms=duration_ms)
    
    def _check_cpu(self) -> Dict[str, Any]:
        threshold = self.cpu_config.get('threshold_percent', 90)
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            is_ok = cpu_percent < threshold
            result = {'status': 'UP' if is_ok else 'DOWN', 'usage_percent': round(cpu_percent, 2), 'threshold': threshold, 'cores': psutil.cpu_count()}
            if is_ok:
                self.logger.debug(f"  ✓ CPU 정상: {cpu_percent}%")
            else:
                self.logger.warning(f"  ✗ CPU 임계값 초과: {cpu_percent}%")
            return result
        except Exception as e:
            self.logger.error(f"  ✗ CPU 체크 실패: {e}")
            return {'status': 'DOWN', 'error': str(e)}
    
    def _check_memory(self) -> Dict[str, Any]:
        threshold = self.memory_config.get('threshold_percent', 90)
        try:
            memory = psutil.virtual_memory()
            is_ok = memory.percent < threshold
            result = {'status': 'UP' if is_ok else 'DOWN', 'usage_percent': round(memory.percent, 2), 'threshold': threshold, 'total_gb': round(memory.total / (1024**3), 2), 'available_gb': round(memory.available / (1024**3), 2), 'used_gb': round(memory.used / (1024**3), 2)}
            if is_ok:
                self.logger.debug(f"  ✓ 메모리 정상: {memory.percent}%")
            else:
                self.logger.warning(f"  ✗ 메모리 임계값 초과: {memory.percent}%")
            return result
        except Exception as e:
            self.logger.error(f"  ✗ 메모리 체크 실패: {e}")
            return {'status': 'DOWN', 'error': str(e)}
    
    def _check_disk(self) -> Dict[str, Any]:
        threshold = self.disk_config.get('threshold_percent', 85)
        paths = self.disk_config.get('paths', ['/'])
        results = {}
        all_ok = True
        for path in paths:
            try:
                disk = psutil.disk_usage(path)
                is_ok = disk.percent < threshold
                results[path] = {'status': 'UP' if is_ok else 'DOWN', 'usage_percent': round(disk.percent, 2), 'threshold': threshold, 'total_gb': round(disk.total / (1024**3), 2), 'free_gb': round(disk.free / (1024**3), 2), 'used_gb': round(disk.used / (1024**3), 2)}
                if is_ok:
                    self.logger.debug(f"  ✓ 디스크 정상 ({path}): {disk.percent}%")
                else:
                    self.logger.warning(f"  ✗ 디스크 임계값 초과 ({path}): {disk.percent}%")
                    all_ok = False
            except Exception as e:
                self.logger.error(f"  ✗ 디스크 체크 실패 ({path}): {e}")
                results[path] = {'status': 'DOWN', 'error': str(e)}
                all_ok = False
        return {'status': 'UP' if all_ok else 'DOWN', 'paths': results}
