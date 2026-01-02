#!/usr/bin/env python3
"""
헬스체크 메인 애플리케이션

Flask 웹 서버를 실행하고 헬스체크 엔드포인트를 제공합니다.

실행 방법:
    python -m app.main
    
또는 Gunicorn으로 실행 (프로덕션):
    gunicorn -w 4 -b 0.0.0.0:8080 app.main:app
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, List

from flask import Flask, jsonify, request

# 설정 및 로깅 import
from app.config import load_config, get_config
from app.logging_utils import setup_logging
from app.checks import (
    PortChecker,
    ProcessChecker,
    HttpChecker,
    ResourceChecker,
    CheckResult
)

# =============================================================================
# 설정 로드
# =============================================================================

CONFIG_PATH = os.getenv('HEALTHZ_CONFIG_PATH', '/opt/healthz/config.yaml')

try:
    config = load_config(CONFIG_PATH)
    print(f"✅ 설정 파일 로드 완료: {CONFIG_PATH}")
except Exception as e:
    print(f"❌ 설정 파일 로드 실패: {e}", file=sys.stderr)
    print("기본 설정을 사용합니다.", file=sys.stderr)
    from app.config import Config
    config = Config.__new__(Config)
    config.config = Config._get_default_config()

# =============================================================================
# 로깅 설정
# =============================================================================

logging_config = config.get('logging', default={})
setup_logging(logging_config)

import logging
logger = logging.getLogger(__name__)

# =============================================================================
# Flask 애플리케이션 초기화
# =============================================================================

app = Flask(__name__)
APP_START_TIME = time.time()

# 애플리케이션 정보
APP_NAME = config.get('application', 'name', default='healthcheck-app')
APP_VERSION = config.get('application', 'version', default='1.0.0')
ENVIRONMENT = config.get('application', 'environment', default='production')

# 서버 설정
SERVER_HOST = config.get('server', 'host', default='0.0.0.0')
SERVER_PORT = config.get('server', 'port', default=8080)

# 엔드포인트 경로
HEALTH_PATH = config.get('endpoints', 'health', default='/health')
HEALTHZ_PATH = config.get('endpoints', 'healthz', default='/healthz')
LIVEZ_PATH = config.get('endpoints', 'livez', default='/livez')
READYZ_PATH = config.get('endpoints', 'readyz', default='/readyz')

# 로깅 옵션
LOG_SUCCESS = logging_config.get('log_success_checks', False)
LOG_REQUESTS = logging_config.get('log_requests', False)

logger.info("=" * 80)
logger.info(f"헬스체크 애플리케이션 초기화")
logger.info(f"  이름: {APP_NAME}")
logger.info(f"  버전: {APP_VERSION}")
logger.info(f"  환경: {ENVIRONMENT}")
logger.info(f"  설정: {CONFIG_PATH}")
logger.info(f"  서버: {SERVER_HOST}:{SERVER_PORT}")
logger.info(f"  엔드포인트: {HEALTH_PATH}, {HEALTHZ_PATH}, {LIVEZ_PATH}, {READYZ_PATH}")
logger.info("=" * 80)

# =============================================================================
# 체커 인스턴스 초기화
# =============================================================================

checkers = {}

port_config = config.get('checks', 'ports', default={})
if port_config.get('enabled', True):
    checkers['ports'] = PortChecker(port_config)
    logger.info(f"✅ 포트 체커 활성화: {port_config.get('targets', [])}")

process_config = config.get('checks', 'processes', default={})
if process_config.get('enabled', True):
    checkers['processes'] = ProcessChecker(process_config)
    logger.info(f"✅ 프로세스 체커 활성화: {process_config.get('targets', [])}")

http_config = config.get('checks', 'http', default={})
if http_config.get('enabled', False):
    checkers['http'] = HttpChecker(http_config)
    logger.info(f"✅ HTTP 체커 활성화: {len(http_config.get('endpoints', []))}개")

resource_config = config.get('checks', 'resources', default={})
if resource_config:
    checkers['resources'] = ResourceChecker(resource_config)
    logger.info(f"✅ 리소스 체커 활성화")

logger.info(f"총 {len(checkers)}개 체커 초기화 완료")
logger.info("=" * 80)

# =============================================================================
# 헬스체크 함수
# =============================================================================

def perform_health_check(check_names: List[str] = None) -> tuple:
    """헬스체크를 수행합니다."""
    start_time = time.time()
    
    if check_names is None:
        check_names = list(checkers.keys())
    
    logger.debug(f"헬스체크 시작: {check_names}")
    
    results = {}
    all_healthy = True
    
    for check_name in check_names:
        checker = checkers.get(check_name)
        if checker is None:
            logger.warning(f"체커를 찾을 수 없음: {check_name}")
            continue
        
        try:
            result: CheckResult = checker.check()
            results[check_name] = result.to_dict()
            if not result.is_healthy():
                all_healthy = False
        except Exception as e:
            logger.error(f"체크 실행 실패 ({check_name}): {e}", exc_info=True)
            results[check_name] = {
                'name': check_name,
                'status': 'DOWN',
                'message': f'Check failed: {str(e)}',
                'error': str(e)
            }
            all_healthy = False
    
    response = {
        'status': 'UP' if all_healthy else 'DOWN',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'application': {
            'name': APP_NAME,
            'version': APP_VERSION,
            'environment': ENVIRONMENT,
            'uptime_seconds': round(time.time() - APP_START_TIME, 2)
        },
        'checks': results,
        'timing': {
            'check_duration_ms': round((time.time() - start_time) * 1000, 2)
        }
    }
    
    timing_config = config.get('timing', default={})
    if timing_config:
        response['configuration'] = {'timing': timing_config}
    
    return all_healthy, response

# =============================================================================
# Flask 라우트
# =============================================================================

@app.before_request
def log_request():
    """요청 로깅"""
    if LOG_REQUESTS:
        logger.debug(f"요청: {request.method} {request.path} (from: {request.remote_addr})")

@app.route('/', methods=['GET'])
def root():
    """루트 엔드포인트 - 서버 정보 반환"""
    return jsonify({
        'service': APP_NAME,
        'version': APP_VERSION,
        'environment': ENVIRONMENT,
        'uptime_seconds': round(time.time() - APP_START_TIME, 2),
        'server': {
            'host': SERVER_HOST,
            'port': SERVER_PORT
        },
        'endpoints': {
            'health': HEALTH_PATH,
            'healthz': HEALTHZ_PATH,
            'livez': LIVEZ_PATH,
            'readyz': READYZ_PATH,
        },
        'checks': {
            'available': list(checkers.keys()),
            'count': len(checkers)
        },
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

@app.route(HEALTH_PATH, methods=['GET', 'HEAD'])
def health():
    """기본 헬스체크 엔드포인트"""
    logger.info(f"[{request.method}] {HEALTH_PATH} 요청 (from: {request.remote_addr})")
    is_healthy, response_data = perform_health_check()
    status_code = 200 if is_healthy else 503
    if is_healthy:
        if LOG_SUCCESS:
            logger.info(f"✅ {HEALTH_PATH} 응답: {status_code} UP")
    else:
        logger.warning(f"⚠️  {HEALTH_PATH} 응답: {status_code} DOWN")
    if request.method == 'HEAD':
        return '', status_code
    return jsonify(response_data), status_code

@app.route(HEALTHZ_PATH, methods=['GET', 'HEAD'])
def healthz():
    """Kubernetes 스타일 헬스체크 엔드포인트"""
    logger.info(f"[{request.method}] {HEALTHZ_PATH} 요청 (from: {request.remote_addr})")
    is_healthy, response_data = perform_health_check()
    status_code = 200 if is_healthy else 503
    if is_healthy:
        if LOG_SUCCESS:
            logger.info(f"✅ {HEALTHZ_PATH} 응답: {status_code} UP")
    else:
        logger.warning(f"⚠️  {HEALTHZ_PATH} 응답: {status_code} DOWN")
    if request.method == 'HEAD':
        return '', status_code
    return jsonify(response_data), status_code

@app.route(LIVEZ_PATH, methods=['GET', 'HEAD'])
def livez():
    """Liveness probe 엔드포인트"""
    logger.info(f"[{request.method}] {LIVEZ_PATH} 요청 (from: {request.remote_addr})")
    liveness_checks = config.get('probes', 'liveness', 'checks', default=['ports', 'processes'])
    is_alive, response_data = perform_health_check(check_names=liveness_checks)
    status_code = 200 if is_alive else 503
    if is_alive:
        if LOG_SUCCESS:
            logger.info(f"✅ {LIVEZ_PATH} 응답: {status_code} ALIVE")
    else:
        logger.warning(f"⚠️  {LIVEZ_PATH} 응답: {status_code} NOT_ALIVE")
    if request.method == 'HEAD':
        return '', status_code
    response_data['probe_type'] = 'liveness'
    response_data['probe_checks'] = liveness_checks
    return jsonify(response_data), status_code

@app.route(READYZ_PATH, methods=['GET', 'HEAD'])
def readyz():
    """Readiness probe 엔드포인트"""
    logger.info(f"[{request.method}] {READYZ_PATH} 요청 (from: {request.remote_addr})")
    readiness_checks = config.get('probes', 'readiness', 'checks', default=['ports', 'processes', 'http', 'resources'])
    is_ready, response_data = perform_health_check(check_names=readiness_checks)
    status_code = 200 if is_ready else 503
    if is_ready:
        if LOG_SUCCESS:
            logger.info(f"✅ {READYZ_PATH} 응답: {status_code} READY")
    else:
        logger.warning(f"⚠️  {READYZ_PATH} 응답: {status_code} NOT_READY")
    if request.method == 'HEAD':
        return '', status_code
    response_data['probe_type'] = 'readiness'
    response_data['probe_checks'] = readiness_checks
    response_data['readiness'] = 'READY' if is_ready else 'NOT_READY'
    return jsonify(response_data), status_code

@app.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': [HEALTH_PATH, HEALTHZ_PATH, LIVEZ_PATH, READYZ_PATH]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500

# =============================================================================
# 메인 실행
# =============================================================================

def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info(f"🚀 헬스체크 서버 시작")
    logger.info(f"  주소: http://{SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"  엔드포인트:")
    logger.info(f"    - {HEALTH_PATH} (전체 헬스체크)")
    logger.info(f"    - {HEALTHZ_PATH} (Kubernetes 스타일)")
    logger.info(f"    - {LIVEZ_PATH} (Liveness probe)")
    logger.info(f"    - {READYZ_PATH} (Readiness probe)")
    logger.info(f"  활성 체커: {', '.join(checkers.keys())}")
    logger.info("=" * 80)
    
    try:
        if ENVIRONMENT == 'development':
            app.run(host=SERVER_HOST, port=SERVER_PORT, debug=True)
        else:
            app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("\n서버 종료 중...")
    except Exception as e:
        logger.error(f"서버 시작 실패: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
