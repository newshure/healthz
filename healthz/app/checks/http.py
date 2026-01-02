# ============================================================
# HTTP Endpoint Health Checker with Response Validation
# HTTP 엔드포인트 헬스 체커 (응답 검증 기능 포함)
# ============================================================

import requests
import urllib3
import json
from typing import List, Dict, Any, Optional
from .base import BaseChecker, CheckResult

# SSL 인증서 검증 경고 비활성화 (verify_ssl=false 사용 시)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HTTPChecker(BaseChecker):
    """
    HTTP/HTTPS 엔드포인트 헬스체크 및 응답 검증을 수행하는 클래스
    
    주요 기능:
    - HTTP/HTTPS 프로토콜 지원
    - SSL 인증서 검증 옵션
    - 다중 엔드포인트 체크
    - 커스텀 HTTP 메소드 지원
    - 상태 코드 검증
    - 응답 본문 검증 (string, number, json)
    - JSON 중첩 필드 접근 (점 표기법)
    - 숫자 비교 연산자 (>, <, >=, <=, ==)
    - 여러 조건 동시 체크 (AND 조건)
    """
    
    def check(self) -> CheckResult:
        """
        설정된 모든 HTTP 엔드포인트의 상태를 체크
        
        Returns:
            CheckResult: 체크 결과 (healthy/unhealthy, 메시지, 상세 정보)
        """
        targets = self.config.get('targets', [])
        
        # 체크할 대상이 없는 경우
        if not targets:
            self.logger.debug("HTTP 체크 대상이 설정되지 않음")
            return CheckResult(True, "No HTTP endpoints configured to check", {})
        
        healthy_endpoints = []    # 정상 엔드포인트 목록
        unhealthy_endpoints = []  # 비정상 엔드포인트 목록
        details_list = []         # 각 엔드포인트의 상세 체크 결과
        
        # 각 엔드포인트 체크
        for target in targets:
            url = target.get('url')
            scheme = target.get('scheme', 'http').lower()  # 기본값: http
            method = target.get('method', 'GET').upper()
            timeout = target.get('timeout', 5)
            expected_status = target.get('expected_status', 200)
            verify_ssl = target.get('verify_ssl', True)
            expected_response = target.get('expected_response')  # 응답 본문 검증 설정
            
            # URL 구성 (scheme이 URL에 포함되어 있지 않은 경우 추가)
            full_url = self._build_full_url(url, scheme)
            
            self.logger.debug(
                f"HTTP 체크 시작: {full_url} "
                f"(method={method}, timeout={timeout}s, "
                f"response_validation={'enabled' if expected_response else 'disabled'})"
            )
            
            # 엔드포인트 체크 실행
            result = self._check_endpoint(
                full_url, 
                method, 
                timeout, 
                expected_status,
                verify_ssl,
                expected_response
            )
            
            # 결과 분류
            if result['healthy']:
                healthy_endpoints.append(full_url)
                validation_msg = ""
                if result.get('response_validation'):
                    validation_msg = " [response validated]"
                self.logger.info(
                    f"HTTP 체크 성공: {full_url} "
                    f"(status={result.get('status_code', 'N/A')}, "
                    f"response_time={result.get('response_time_ms', 'N/A')}ms{validation_msg})"
                )
            else:
                unhealthy_endpoints.append(full_url)
                error_msg = result.get('error', 'Unknown error')
                self.logger.warning(f"HTTP 체크 실패: {full_url} - {error_msg}")
            
            # 상세 정보 저장
            details_list.append({
                'url': full_url,
                'scheme': scheme,
                'method': method,
                'healthy': result['healthy'],
                'status_code': result.get('status_code'),
                'response_time_ms': result.get('response_time_ms'),
                'error': result.get('error'),
                'response_validation': result.get('response_validation')
            })
        
        # 전체 결과 판단 (모든 엔드포인트가 정상이어야 healthy)
        healthy = len(unhealthy_endpoints) == 0
        message = f"{len(healthy_endpoints)}/{len(targets)} endpoints healthy"
        
        details = {
            "healthy": healthy_endpoints,
            "unhealthy": unhealthy_endpoints,
            "details": details_list
        }
        
        return CheckResult(healthy, message, details)
    
    def _build_full_url(self, url: str, scheme: str) -> str:
        """
        URL에 scheme을 추가하여 완전한 URL 생성
        
        Args:
            url: 원본 URL (scheme 포함 여부 무관)
            scheme: 사용할 scheme (http 또는 https)
        
        Returns:
            str: 완전한 URL (scheme 포함)
        """
        # 이미 scheme이 포함된 경우 (http:// 또는 https://)
        if url.startswith('http://') or url.startswith('https://'):
            self.logger.debug(f"URL에 이미 scheme이 포함되어 있음: {url}")
            return url
        
        # scheme이 없는 경우 추가
        full_url = f"{scheme}://{url}"
        self.logger.debug(f"URL에 scheme 추가: {url} -> {full_url}")
        return full_url
    
    def _check_endpoint(
        self, 
        url: str, 
        method: str, 
        timeout: int, 
        expected_status: int,
        verify_ssl: bool,
        expected_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        개별 HTTP 엔드포인트 체크 수행 (응답 검증 포함)
        
        Args:
            url: 체크할 완전한 URL
            method: HTTP 메소드 (GET, POST 등)
            timeout: 요청 타임아웃 (초)
            expected_status: 예상 HTTP 상태 코드
            verify_ssl: SSL 인증서 검증 여부 (HTTPS인 경우)
            expected_response: 응답 본문 검증 설정 (선택사항)
        
        Returns:
            Dict[str, Any]: 체크 결과
                - healthy: bool (성공 여부)
                - status_code: int (HTTP 상태 코드)
                - response_time_ms: int (응답 시간, 밀리초)
                - response_validation: dict (응답 검증 결과)
                - error: str (에러 메시지, 실패 시)
        """
        try:
            # HTTP 요청 수행 및 응답 시간 측정
            import time
            start_time = time.time()
            
            response = requests.request(
                method=method,
                url=url,
                timeout=timeout,
                verify=verify_ssl,      # SSL 인증서 검증 여부
                allow_redirects=True    # 리다이렉트 허용
            )
            
            # 응답 시간 계산 (밀리초)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 1단계: 상태 코드 검증
            status_healthy = response.status_code == expected_status
            
            result = {
                'healthy': status_healthy,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'response_time_ms': response_time_ms
            }
            
            # 상태 코드가 일치하지 않으면 즉시 실패 반환
            if not status_healthy:
                result['error'] = (
                    f"Status code mismatch: expected {expected_status}, "
                    f"got {response.status_code}"
                )
                return result
            
            # 2단계: 응답 본문 검증 (설정된 경우)
            if expected_response:
                self.logger.debug(f"응답 본문 검증 시작: {url}")
                validation_result = self._validate_response(
                    response, 
                    expected_response
                )
                result['response_validation'] = validation_result
                
                # 응답 검증 실패 시
                if not validation_result['valid']:
                    result['healthy'] = False
                    result['error'] = validation_result['error']
                    self.logger.debug(
                        f"응답 본문 검증 실패: {validation_result['error']}"
                    )
                else:
                    self.logger.debug("응답 본문 검증 성공")
            
            return result
            
        except requests.exceptions.SSLError as e:
            # SSL 인증서 관련 에러
            self.logger.error(f"HTTP 체크 SSL 에러 ({url}): {str(e)}")
            return {
                'healthy': False,
                'error': f"SSL certificate error: {str(e)}"
            }
        
        except requests.exceptions.Timeout as e:
            # 타임아웃 에러
            self.logger.error(f"HTTP 체크 타임아웃 ({url}): {str(e)}")
            return {
                'healthy': False,
                'error': f"Request timeout after {timeout}s"
            }
        
        except requests.exceptions.ConnectionError as e:
            # 연결 에러 (호스트 접근 불가, 포트 닫힘 등)
            self.logger.error(f"HTTP 체크 연결 에러 ({url}): {str(e)}")
            return {
                'healthy': False,
                'error': f"Connection error: {str(e)}"
            }
        
        except requests.exceptions.RequestException as e:
            # 기타 요청 에러
            self.logger.error(f"HTTP 체크 요청 에러 ({url}): {str(e)}")
            return {
                'healthy': False,
                'error': f"Request error: {str(e)}"
            }
        
        except Exception as e:
            # 예상치 못한 에러
            self.logger.error(f"HTTP 체크 예외 발생 ({url}): {str(e)}")
            return {
                'healthy': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    def _validate_response(
        self, 
        response: requests.Response, 
        expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        응답 본문 검증 (타입에 따라 다른 검증 로직 적용)
        
        Args:
            response: HTTP 응답 객체
            expected: 검증 설정 (type, field, value 등)
        
        Returns:
            Dict[str, Any]: 검증 결과
                - valid: bool (검증 성공 여부)
                - error: str (에러 메시지, 실패 시)
                - expected: Any (예상 값)
                - actual: Any (실제 값)
        """
        try:
            response_type = expected.get('type', 'string').lower()
            
            # 응답 타입에 따라 적절한 검증 메소드 호출
            if response_type == 'json':
                return self._validate_json_response(response, expected)
            elif response_type in ['string', 'text']:
                return self._validate_string_response(response, expected)
            elif response_type == 'number':
                return self._validate_number_response(response, expected)
            else:
                return {
                    'valid': False,
                    'error': f"Unsupported response type: {response_type}"
                }
        
        except Exception as e:
            return {
                'valid': False,
                'error': f"Response validation error: {str(e)}"
            }
    
    def _validate_json_response(
        self, 
        response: requests.Response, 
        expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        JSON 응답 검증
        
        지원 기능:
        - 단일 필드 값 체크 (field, value, operator)
        - 여러 조건 동시 체크 (checks 리스트)
        - 중첩 필드 접근 (점 표기법: data.database.status)
        - 숫자 비교 연산자 (equals, greater_than, less_than 등)
        
        Args:
            response: HTTP 응답 객체
            expected: 검증 설정
        
        Returns:
            Dict[str, Any]: 검증 결과
        """
        try:
            # JSON 파싱
            response_json = response.json()
            
            # 케이스 1: 여러 조건 체크 (checks 리스트)
            if 'checks' in expected:
                self.logger.debug(f"여러 조건 체크 시작 (총 {len(expected['checks'])}개)")
                
                for idx, check in enumerate(expected['checks']):
                    field = check.get('field')
                    expected_value = check.get('value')
                    operator = check.get('operator', 'equals')
                    
                    # 중첩 필드 값 가져오기
                    actual_value = self._get_nested_value(response_json, field)
                    
                    self.logger.debug(
                        f"조건 #{idx+1}: field='{field}', "
                        f"expected={expected_value}, actual={actual_value}, "
                        f"operator={operator}"
                    )
                    
                    # 값 비교
                    if not self._compare_values(actual_value, expected_value, operator):
                        return {
                            'valid': False,
                            'error': (
                                f"Field '{field}': expected {expected_value} "
                                f"({operator}), got {actual_value}"
                            ),
                            'expected': expected_value,
                            'actual': actual_value
                        }
                
                self.logger.debug("모든 조건 체크 통과")
            
            # 케이스 2: 단일 필드 체크
            elif 'field' in expected:
                field = expected['field']
                expected_value = expected['value']
                operator = expected.get('operator', 'equals')
                
                # 중첩 필드 값 가져오기
                actual_value = self._get_nested_value(response_json, field)
                
                self.logger.debug(
                    f"단일 필드 체크: field='{field}', "
                    f"expected={expected_value}, actual={actual_value}, "
                    f"operator={operator}"
                )
                
                # 값 비교
                if not self._compare_values(actual_value, expected_value, operator):
                    return {
                        'valid': False,
                        'error': (
                            f"Field '{field}': expected {expected_value} "
                            f"({operator}), got {actual_value}"
                        ),
                        'expected': expected_value,
                        'actual': actual_value
                    }
            
            return {'valid': True}
        
        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'error': f"Invalid JSON response: {str(e)}"
            }
    
    def _validate_string_response(
        self, 
        response: requests.Response, 
        expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        문자열 응답 검증
        
        지원 기능:
        - equals: 정확히 일치하는지 체크
        - contains: 특정 문자열 포함 여부 체크
        
        Args:
            response: HTTP 응답 객체
            expected: 검증 설정
        
        Returns:
            Dict[str, Any]: 검증 결과
        """
        response_text = response.text
        
        # 케이스 1: 정확히 일치하는지 체크
        if 'equals' in expected:
            expected_text = str(expected['equals'])
            self.logger.debug(
                f"문자열 정확히 일치 체크: expected='{expected_text}'"
            )
            
            if response_text == expected_text:
                return {'valid': True}
            else:
                return {
                    'valid': False,
                    'error': (
                        f"Response mismatch: expected '{expected_text}', "
                        f"got '{response_text}'"
                    ),
                    'expected': expected_text,
                    'actual': response_text
                }
        
        # 케이스 2: 포함 여부 체크
        if 'contains' in expected:
            expected_substring = str(expected['contains'])
            self.logger.debug(
                f"문자열 포함 여부 체크: expected contains '{expected_substring}'"
            )
            
            if expected_substring in response_text:
                return {'valid': True}
            else:
                return {
                    'valid': False,
                    'error': f"Response does not contain '{expected_substring}'",
                    'expected': f"Contains '{expected_substring}'",
                    'actual': response_text[:100]  # 처음 100자만 표시
                }
        
        return {'valid': True}
    
    def _validate_number_response(
        self, 
        response: requests.Response, 
        expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        숫자 응답 검증
        
        응답 본문 전체가 숫자인 경우 (예: "42", "3.14")
        
        Args:
            response: HTTP 응답 객체
            expected: 검증 설정
        
        Returns:
            Dict[str, Any]: 검증 결과
        """
        try:
            response_number = float(response.text)
            expected_value = float(expected['value'])
            operator = expected.get('operator', 'equals')
            
            self.logger.debug(
                f"숫자 비교: actual={response_number}, "
                f"expected={expected_value}, operator={operator}"
            )
            
            if self._compare_values(response_number, expected_value, operator):
                return {'valid': True}
            else:
                return {
                    'valid': False,
                    'error': (
                        f"Number check failed: {response_number} "
                        f"{operator} {expected_value}"
                    ),
                    'expected': expected_value,
                    'actual': response_number
                }
        
        except ValueError as e:
            return {
                'valid': False,
                'error': f"Invalid number response: {str(e)}"
            }
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        중첩된 JSON 필드 값 가져오기 (점 표기법 지원)
        
        예시:
        - "status" -> data["status"]
        - "data.database.status" -> data["data"]["database"]["status"]
        
        Args:
            data: JSON 데이터 (dict)
            field_path: 필드 경로 (점으로 구분)
        
        Returns:
            Any: 필드 값 (없으면 None)
        """
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                self.logger.debug(f"필드 '{field_path}'를 찾을 수 없음 (중단 위치: '{key}')")
                return None
        
        return value
    
    def _compare_values(self, actual: Any, expected: Any, operator: str) -> bool:
        """
        값 비교 (다양한 연산자 지원)
        
        지원 연산자:
        - equals: 같음 (기본값)
        - greater_than: 큼 (>)
        - less_than: 작음 (<)
        - greater_equal: 크거나 같음 (>=)
        - less_equal: 작거나 같음 (<=)
        
        Args:
            actual: 실제 값
            expected: 예상 값
            operator: 비교 연산자
        
        Returns:
            bool: 비교 결과
        """
        try:
            if operator == 'equals':
                return actual == expected
            elif operator == 'greater_than':
                return actual > expected
            elif operator == 'less_than':
                return actual < expected
            elif operator == 'greater_equal':
                return actual >= expected
            elif operator == 'less_equal':
                return actual <= expected
            else:
                self.logger.warning(
                    f"알 수 없는 연산자: {operator}, 'equals'로 대체"
                )
                return actual == expected
        except TypeError as e:
            self.logger.error(
                f"값 비교 오류: actual={actual}, expected={expected}, "
                f"operator={operator}, error={str(e)}"
            )
            return False
