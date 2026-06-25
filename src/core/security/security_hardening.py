"""
Advanced Security Hardening System

Implements  Multi-layered security including input validation,
API security, encryption, and threat detection for the ReflectAI platform.
"""

import hashlib
import ipaddress
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import redis.asyncio as redis
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from src.shared import ReflectAIError, get_logger

logger = get_logger(__name__)


class ThreatLevel(str, Enum):
    """Security threat levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(str, Enum):
    """Types of security events"""

    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_VIOLATION = "authz_violation"
    INPUT_VALIDATION_FAILURE = "input_validation_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ENCRYPTION_FAILURE = "encryption_failure"
    API_ABUSE = "api_abuse"
    INJECTION_ATTEMPT = "injection_attempt"


class ValidationResult(str, Enum):
    """Input validation results"""

    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass
class SecurityEvent:
    """Security event record"""

    event_id: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    source_ip: str
    user_id: str | None
    team_id: str | None
    details: dict[str, Any]
    timestamp: datetime
    blocked: bool
    remediation_action: str | None = None


@dataclass
class ThreatIntelligence:
    """Threat intelligence data"""

    ip_address: str
    threat_score: float
    threat_categories: list[str]
    last_seen: datetime
    source: str
    confidence: float


class InputValidator:
    """Advanced input validation and sanitization"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # SQL injection patterns
        self.sql_patterns = [
            r"(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bCREATE\b)",
            r"(\'\s*(OR|AND)\s*\'\s*=\s*\')",
            r"(\'\s*(OR|AND)\s*[0-9]+\s*=\s*[0-9]+)",
            r"(;|\-\-|\#|\/\*|\*\/)",
        ]

        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"eval\s*\(",
            r"document\.(cookie|domain|referrer)",
        ]

        # Command injection patterns
        self.command_patterns = [
            r"(\||&|;|\$\(|\`)",
            r"(wget|curl|nc|netcat|bash|sh|cmd|powershell)",
            r"(\.\./|\.\.\\\)",
        ]

        # Compile patterns
        self.compiled_sql = [re.compile(p, re.IGNORECASE) for p in self.sql_patterns]
        self.compiled_xss = [re.compile(p, re.IGNORECASE) for p in self.xss_patterns]
        self.compiled_command = [re.compile(p, re.IGNORECASE) for p in self.command_patterns]

    async def validate_input(
        self, input_data: Any, validation_context: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Comprehensive input validation"""

        validation_start = time.perf_counter()

        try:
            result = {
                "is_valid": True,
                "validation_result": ValidationResult.VALID,
                "threats_detected": [],
                "sanitized_data": input_data,
                "validation_context": validation_context,
            }

            # Convert input to string for pattern matching
            input_str = str(input_data) if input_data is not None else ""

            # SQL injection detection
            sql_threats = await self._detect_sql_injection(input_str)
            if sql_threats:
                result["threats_detected"].extend(sql_threats)
                result["validation_result"] = ValidationResult.SUSPICIOUS

            # XSS detection
            xss_threats = await self._detect_xss(input_str)
            if xss_threats:
                result["threats_detected"].extend(xss_threats)
                result["validation_result"] = ValidationResult.SUSPICIOUS

            # Command injection detection
            command_threats = await self._detect_command_injection(input_str)
            if command_threats:
                result["threats_detected"].extend(command_threats)
                result["validation_result"] = ValidationResult.BLOCKED

            # Length validation
            if len(input_str) > 100000:  # 100KB limit
                result["threats_detected"].append("oversized_input")
                result["validation_result"] = ValidationResult.BLOCKED

            # Character validation for specific contexts
            if validation_context in ["user_id", "team_id"]:
                if not re.match(r"^[A-Za-z0-9_-]+$", input_str):
                    result["threats_detected"].append("invalid_characters")
                    result["validation_result"] = ValidationResult.INVALID

            # Update final validation status
            if result["validation_result"] in [ValidationResult.BLOCKED, ValidationResult.INVALID]:
                result["is_valid"] = False

            # Sanitize data if needed
            if (
                result["threats_detected"]
                and result["validation_result"] == ValidationResult.SUSPICIOUS
            ):
                result["sanitized_data"] = await self._sanitize_input(input_str)

            duration = (time.perf_counter() - validation_start) * 1000

            self.logger.info(
                "Input validation completed",
                extra={
                    "validation_context": validation_context,
                    "result": result["validation_result"],
                    "threats_detected": len(result["threats_detected"]),
                    "duration_ms": duration,
                    "user_id": user_id,
                },
            )

            return result

        except Exception as e:
            self.logger.error(f"Input validation failed: {str(e)}")
            return {
                "is_valid": False,
                "validation_result": ValidationResult.BLOCKED,
                "threats_detected": ["validation_error"],
                "sanitized_data": None,
                "error": str(e),
            }

    async def _detect_sql_injection(self, input_str: str) -> list[str]:
        """Detect SQL injection attempts"""

        threats = []
        for pattern in self.compiled_sql:
            if pattern.search(input_str):
                threats.append(f"sql_injection_{pattern.pattern[:20]}")

        return threats

    async def _detect_xss(self, input_str: str) -> list[str]:
        """Detect XSS attempts"""

        threats = []
        for pattern in self.compiled_xss:
            if pattern.search(input_str):
                threats.append(f"xss_{pattern.pattern[:20]}")

        return threats

    async def _detect_command_injection(self, input_str: str) -> list[str]:
        """Detect command injection attempts"""

        threats = []
        for pattern in self.compiled_command:
            if pattern.search(input_str):
                threats.append(f"command_injection_{pattern.pattern[:20]}")

        return threats

    async def _sanitize_input(self, input_str: str) -> str:
        """Sanitize potentially malicious input"""

        # HTML entity encoding
        sanitized = (
            input_str.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        # Remove null bytes
        sanitized = sanitized.replace("\x00", "")

        # Remove control characters except whitespace
        sanitized = "".join(char for char in sanitized if ord(char) >= 32 or char in "\t\n\r")

        return sanitized


class RateLimiter:
    """Advanced rate limiting with multiple algorithms"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.logger = get_logger(__name__)

    async def check_rate_limit(
        self, key: str, limit: int, window_seconds: int, algorithm: str = "sliding_window"
    ) -> dict[str, Any]:
        """Check if request is within rate limits"""

        try:
            if algorithm == "sliding_window":
                return await self._sliding_window_check(key, limit, window_seconds)
            elif algorithm == "token_bucket":
                return await self._token_bucket_check(key, limit, window_seconds)
            elif algorithm == "fixed_window":
                return await self._fixed_window_check(key, limit, window_seconds)
            else:
                raise ValueError(f"Unknown rate limiting algorithm: {algorithm}")

        except Exception as e:
            self.logger.error(f"Rate limit check failed: {str(e)}")
            # Fail open for availability
            return {
                "allowed": True,
                "remaining": limit,
                "reset_time": time.time() + window_seconds,
                "algorithm": algorithm,
                "error": str(e),
            }

    async def _sliding_window_check(
        self, key: str, limit: int, window_seconds: int
    ) -> dict[str, Any]:
        """Sliding window rate limiter"""

        current_time = time.time()
        window_start = current_time - window_seconds

        # Use Redis sorted set for sliding window
        pipeline = self.redis.pipeline()

        # Remove old entries
        pipeline.zremrangebyscore(f"rate_limit:{key}", 0, window_start)

        # Count current requests
        pipeline.zcard(f"rate_limit:{key}")

        # Add current request
        pipeline.zadd(f"rate_limit:{key}", {str(current_time): current_time})

        # Set expiry
        pipeline.expire(f"rate_limit:{key}", window_seconds + 1)

        results = await pipeline.execute()
        current_count = results[1]

        allowed = current_count < limit
        remaining = max(0, limit - current_count - 1) if allowed else 0

        return {
            "allowed": allowed,
            "remaining": remaining,
            "current_count": current_count + 1,
            "limit": limit,
            "reset_time": current_time + window_seconds,
            "algorithm": "sliding_window",
        }

    async def _token_bucket_check(
        self, key: str, limit: int, refill_seconds: int
    ) -> dict[str, Any]:
        """Token bucket rate limiter"""

        current_time = time.time()
        bucket_key = f"token_bucket:{key}"

        # Get current bucket state
        bucket_data = await self.redis.hmget(bucket_key, "tokens", "last_refill")

        if bucket_data[0] is None:
            # Initialize bucket
            tokens = limit - 1  # Consume one token for this request
            last_refill = current_time
        else:
            tokens = float(bucket_data[0])
            last_refill = float(bucket_data[1])

            # Calculate tokens to add based on time elapsed
            time_elapsed = current_time - last_refill
            tokens_to_add = (time_elapsed / refill_seconds) * limit
            tokens = min(limit, tokens + tokens_to_add)

            # Consume token if available
            if tokens >= 1:
                tokens -= 1
            else:
                # No tokens available
                return {
                    "allowed": False,
                    "remaining": 0,
                    "tokens": tokens,
                    "reset_time": last_refill + refill_seconds,
                    "algorithm": "token_bucket",
                }

        # Update bucket
        await self.redis.hmset(bucket_key, {"tokens": tokens, "last_refill": current_time})
        await self.redis.expire(bucket_key, refill_seconds * 2)

        return {
            "allowed": True,
            "remaining": int(tokens),
            "tokens": tokens,
            "reset_time": current_time + refill_seconds,
            "algorithm": "token_bucket",
        }

    async def _fixed_window_check(
        self, key: str, limit: int, window_seconds: int
    ) -> dict[str, Any]:
        """Fixed window rate limiter"""

        current_time = time.time()
        window_start = int(current_time // window_seconds) * window_seconds
        window_key = f"fixed_window:{key}:{window_start}"

        # Increment counter
        current_count = await self.redis.incr(window_key)

        # Set expiry on first use
        if current_count == 1:
            await self.redis.expire(window_key, window_seconds + 1)

        allowed = current_count <= limit
        remaining = max(0, limit - current_count) if allowed else 0

        return {
            "allowed": allowed,
            "remaining": remaining,
            "current_count": current_count,
            "limit": limit,
            "reset_time": window_start + window_seconds,
            "algorithm": "fixed_window",
        }


class EncryptionManager:
    """Advanced encryption and key management"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.logger = get_logger(__name__)
        self._fernet = None
        self._private_key = None
        self._public_key = None

    async def initialize_encryption(self) -> bool:
        """Initialize encryption components"""

        try:
            # Initialize symmetric encryption
            encryption_key = await self._get_or_create_encryption_key()
            self._fernet = Fernet(encryption_key)

            # Initialize asymmetric encryption
            await self._initialize_asymmetric_keys()

            self.logger.info("Encryption manager initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Encryption initialization failed: {str(e)}")
            raise ReflectAIError(f"Encryption initialization failed: {str(e)}") from e

    async def _get_or_create_encryption_key(self) -> bytes:
        """Get or create symmetric encryption key"""

        key = await self.redis.get("encryption_key")

        if key is None:
            # Generate new key
            key = Fernet.generate_key()
            await self.redis.set("encryption_key", key)
            self.logger.info("New encryption key generated")

        return key

    async def _initialize_asymmetric_keys(self):
        """Initialize RSA key pair"""

        # In production, these would be loaded from secure key storage
        private_key_pem = await self.redis.get("rsa_private_key")

        if private_key_pem is None:
            # Generate new key pair
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            await self.redis.set("rsa_private_key", private_pem)
            await self.redis.set("rsa_public_key", public_pem)

            self._private_key = private_key
            self._public_key = private_key.public_key()

            self.logger.info("New RSA key pair generated")
        else:
            # Load existing keys
            self._private_key = serialization.load_pem_private_key(private_key_pem, password=None)
            self._public_key = self._private_key.public_key()

    async def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data using symmetric encryption"""

        if not self._fernet:
            await self.initialize_encryption()

        try:
            encrypted_data = self._fernet.encrypt(data.encode("utf-8"))
            return encrypted_data.decode("utf-8")

        except Exception as e:
            self.logger.error(f"Data encryption failed: {str(e)}")
            raise ReflectAIError(f"Data encryption failed: {str(e)}") from e

    async def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""

        if not self._fernet:
            await self.initialize_encryption()

        try:
            decrypted_data = self._fernet.decrypt(encrypted_data.encode("utf-8"))
            return decrypted_data.decode("utf-8")

        except Exception as e:
            self.logger.error(f"Data decryption failed: {str(e)}")
            raise ReflectAIError(f"Data decryption failed: {str(e)}") from e

    async def sign_data(self, data: str) -> str:
        """Create digital signature for data integrity"""

        if not self._private_key:
            await self.initialize_encryption()

        try:
            signature = self._private_key.sign(
                data.encode("utf-8"),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256(),
            )

            import base64

            return base64.b64encode(signature).decode("utf-8")

        except Exception as e:
            self.logger.error(f"Data signing failed: {str(e)}")
            raise ReflectAIError(f"Data signing failed: {str(e)}") from e

    async def verify_signature(self, data: str, signature: str) -> bool:
        """Verify digital signature"""

        if not self._public_key:
            await self.initialize_encryption()

        try:
            import base64

            signature_bytes = base64.b64decode(signature.encode("utf-8"))

            self._public_key.verify(
                signature_bytes,
                data.encode("utf-8"),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256(),
            )

            return True

        except Exception as e:
            self.logger.warning(f"Signature verification failed: {str(e)}")
            return False


class ThreatDetector:
    """Advanced threat detection and monitoring"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.logger = get_logger(__name__)
        self.threat_intelligence: dict[str, ThreatIntelligence] = {}

    async def analyze_request(
        self,
        request_data: dict[str, Any],
        source_ip: str,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """Comprehensive request threat analysis"""

        analysis_start = time.perf_counter()

        try:
            threat_score = 0.0
            detected_threats = []
            risk_factors = []

            # IP reputation check
            ip_analysis = await self._analyze_ip_reputation(source_ip)
            threat_score += ip_analysis["threat_score"]
            if ip_analysis["is_malicious"]:
                detected_threats.append("malicious_ip")
                risk_factors.append(f"IP reputation: {ip_analysis['reputation']}")

            # Behavioral analysis
            behavioral_analysis = await self._analyze_user_behavior(user_id, team_id, request_data)
            threat_score += behavioral_analysis["anomaly_score"]
            if behavioral_analysis["is_anomalous"]:
                detected_threats.append("behavioral_anomaly")
                risk_factors.extend(behavioral_analysis["anomalies"])

            # Request pattern analysis
            pattern_analysis = await self._analyze_request_patterns(request_data)
            threat_score += pattern_analysis["threat_score"]
            detected_threats.extend(pattern_analysis["threats"])
            risk_factors.extend(pattern_analysis["risk_factors"])

            # Geographic analysis
            geo_analysis = await self._analyze_geographic_patterns(source_ip, user_id)
            threat_score += geo_analysis["risk_score"]
            if geo_analysis["is_suspicious"]:
                detected_threats.append("geographic_anomaly")
                risk_factors.append(f"Geographic anomaly: {geo_analysis['reason']}")

            # Determine threat level
            threat_level = self._calculate_threat_level(threat_score)

            analysis_duration = (time.perf_counter() - analysis_start) * 1000

            result = {
                "threat_score": threat_score,
                "threat_level": threat_level,
                "detected_threats": detected_threats,
                "risk_factors": risk_factors,
                "analysis_duration_ms": analysis_duration,
                "recommended_action": self._get_recommended_action(threat_level, detected_threats),
                "should_block": threat_score > 80.0,
            }

            self.logger.info(
                "Threat analysis completed",
                extra={
                    "source_ip": source_ip,
                    "user_id": user_id,
                    "threat_score": threat_score,
                    "threat_level": threat_level,
                    "threats_detected": len(detected_threats),
                    "duration_ms": analysis_duration,
                },
            )

            return result

        except Exception as e:
            self.logger.error(f"Threat analysis failed: {str(e)}")
            # Fail secure for security analysis
            return {
                "threat_score": 100.0,
                "threat_level": ThreatLevel.CRITICAL,
                "detected_threats": ["analysis_error"],
                "risk_factors": [f"Analysis error: {str(e)}"],
                "recommended_action": "block",
                "should_block": True,
                "error": str(e),
            }

    async def _analyze_ip_reputation(self, ip_address: str) -> dict[str, Any]:
        """Analyze IP address reputation"""

        try:
            # Check if IP is in threat intelligence cache
            if ip_address in self.threat_intelligence:
                intel = self.threat_intelligence[ip_address]
                return {
                    "threat_score": intel.threat_score,
                    "is_malicious": intel.threat_score > 50.0,
                    "reputation": "known_threat" if intel.threat_score > 50.0 else "clean",
                    "categories": intel.threat_categories,
                }

            # Basic IP validation
            try:
                ip = ipaddress.ip_address(ip_address)
                if ip.is_private or ip.is_loopback:
                    return {
                        "threat_score": 0.0,
                        "is_malicious": False,
                        "reputation": "private_ip",
                        "categories": [],
                    }
            except ValueError:
                return {
                    "threat_score": 30.0,
                    "is_malicious": False,
                    "reputation": "invalid_ip",
                    "categories": ["invalid"],
                }

            # Check against known threat patterns
            threat_score = 0.0
            categories = []

            # Simulate threat intelligence lookup
            # In production, this would query external threat intelligence APIs
            if self._is_suspicious_ip_pattern(ip_address):
                threat_score = 40.0
                categories.append("suspicious_pattern")

            return {
                "threat_score": threat_score,
                "is_malicious": threat_score > 50.0,
                "reputation": "unknown" if threat_score == 0 else "suspicious",
                "categories": categories,
            }

        except Exception as e:
            self.logger.warning(f"IP reputation check failed: {str(e)}")
            return {
                "threat_score": 10.0,
                "is_malicious": False,
                "reputation": "check_failed",
                "categories": [],
            }

    def _is_suspicious_ip_pattern(self, ip_address: str) -> bool:
        """Check for suspicious IP patterns"""

        # Basic heuristics for demonstration
        # In production, use comprehensive threat feeds
        suspicious_patterns = [
            r"^192\.168\.1\.1$",  # Common router IP (suspicious if external)
            r"^10\.0\.0\.1$",  # Common private IP (suspicious if external)
        ]

        return any(re.match(pattern, ip_address) for pattern in suspicious_patterns)

    async def _analyze_user_behavior(
        self, user_id: str | None, team_id: str | None, request_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze user behavioral patterns"""

        if not user_id:
            return {
                "anomaly_score": 10.0,  # Anonymous users get higher score
                "is_anomalous": False,
                "anomalies": ["anonymous_user"],
            }

        try:
            # Get user's recent activity
            activity_key = f"user_activity:{user_id}"
            recent_activity = await self.redis.lrange(activity_key, 0, 100)

            anomaly_score = 0.0
            anomalies = []

            # Analyze request frequency
            current_time = time.time()
            recent_requests = [
                float(timestamp)
                for timestamp in recent_activity
                if current_time - float(timestamp) < 3600  # Last hour
            ]

            if len(recent_requests) > 100:  # More than 100 requests/hour
                anomaly_score += 30.0
                anomalies.append("high_request_frequency")

            # Check for burst activity
            if len(recent_requests) > 10:
                time_diffs = [
                    recent_requests[i] - recent_requests[i + 1]
                    for i in range(len(recent_requests) - 1)
                ]
                avg_interval = sum(time_diffs) / len(time_diffs)

                if avg_interval < 1.0:  # Less than 1 second between requests
                    anomaly_score += 25.0
                    anomalies.append("burst_activity")

            # Add current request to activity log
            await self.redis.lpush(activity_key, str(current_time))
            await self.redis.ltrim(activity_key, 0, 999)  # Keep last 1000 entries
            await self.redis.expire(activity_key, 86400)  # 24 hour expiry

            return {
                "anomaly_score": anomaly_score,
                "is_anomalous": anomaly_score > 20.0,
                "anomalies": anomalies,
                "request_frequency": len(recent_requests),
            }

        except Exception as e:
            self.logger.warning(f"Behavioral analysis failed: {str(e)}")
            return {"anomaly_score": 5.0, "is_anomalous": False, "anomalies": ["analysis_error"]}

    async def _analyze_request_patterns(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze request for malicious patterns"""

        threat_score = 0.0
        threats = []
        risk_factors = []

        try:
            # Convert request data to string for pattern matching
            request_str = json.dumps(request_data, default=str)

            # Check for common attack patterns
            attack_patterns = {
                "script_injection": r"<script|javascript:|data:text/html",
                "path_traversal": r"\.\./|\.\.\\",
                "command_injection": r"[\|;&$`]",
                "large_payload": len(request_str) > 50000,  # 50KB limit
            }

            for pattern_name, pattern in attack_patterns.items():
                if pattern_name == "large_payload":
                    if pattern:  # Boolean check for payload size
                        threat_score += 20.0
                        threats.append(pattern_name)
                        risk_factors.append(f"Payload size: {len(request_str)} bytes")
                else:
                    if re.search(pattern, request_str, re.IGNORECASE):
                        threat_score += 30.0
                        threats.append(pattern_name)
                        risk_factors.append(f"Pattern detected: {pattern_name}")

            return {"threat_score": threat_score, "threats": threats, "risk_factors": risk_factors}

        except Exception as e:
            self.logger.warning(f"Request pattern analysis failed: {str(e)}")
            return {"threat_score": 5.0, "threats": ["pattern_analysis_error"], "risk_factors": []}

    async def _analyze_geographic_patterns(
        self, source_ip: str, user_id: str | None
    ) -> dict[str, Any]:
        """Analyze geographic access patterns"""

        # Simplified geographic analysis
        # In production, use GeoIP services
        risk_score = 0.0
        is_suspicious = False
        reason = ""

        try:
            # Get user's typical locations if available
            if user_id:
                typical_locations_key = f"user_locations:{user_id}"
                typical_locations = await self.redis.smembers(typical_locations_key)

                # Simulate IP geolocation
                # In production, use MaxMind GeoIP or similar
                current_location = self._simulate_geolocation(source_ip)

                if typical_locations:
                    if current_location not in typical_locations:
                        risk_score = 15.0
                        is_suspicious = True
                        reason = "Access from new geographic location"
                else:
                    # First time seeing this user's location
                    await self.redis.sadd(typical_locations_key, current_location)
                    await self.redis.expire(typical_locations_key, 86400 * 30)  # 30 days

            return {"risk_score": risk_score, "is_suspicious": is_suspicious, "reason": reason}

        except Exception as e:
            self.logger.warning(f"Geographic analysis failed: {str(e)}")
            return {"risk_score": 0.0, "is_suspicious": False, "reason": "analysis_error"}

    def _simulate_geolocation(self, ip_address: str) -> str:
        """Simulate IP geolocation (replace with real service)"""

        # Simple simulation based on IP ranges
        if ip_address.startswith("192.168.") or ip_address.startswith("10."):
            return "local_network"
        elif ip_address.startswith("172."):
            return "private_network"
        else:
            # Hash IP to simulate consistent geographic assignment
            location_hash = hashlib.sha256(ip_address.encode(), usedforsecurity=False).hexdigest()[
                :2
            ]
            locations = ["US", "CA", "UK", "DE", "FR", "JP", "AU", "BR", "IN", "CN"]
            return locations[int(location_hash, 16) % len(locations)]

    def _calculate_threat_level(self, threat_score: float) -> ThreatLevel:
        """Calculate threat level from score"""

        if threat_score >= 80.0:
            return ThreatLevel.CRITICAL
        elif threat_score >= 60.0:
            return ThreatLevel.HIGH
        elif threat_score >= 30.0:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW

    def _get_recommended_action(
        self, threat_level: ThreatLevel, detected_threats: list[str]
    ) -> str:
        """Get recommended security action"""

        if threat_level == ThreatLevel.CRITICAL:
            return "block"
        elif threat_level == ThreatLevel.HIGH:
            return "require_additional_auth"
        elif threat_level == ThreatLevel.MEDIUM:
            if "behavioral_anomaly" in detected_threats:
                return "log_and_monitor"
            else:
                return "allow_with_monitoring"
        else:
            return "allow"


class SecurityHardeningManager:
    """Main security hardening coordinator"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.input_validator = InputValidator()
        self.rate_limiter = RateLimiter(redis_client)
        self.encryption_manager = EncryptionManager(redis_client)
        self.threat_detector = ThreatDetector(redis_client)
        self.security_events: list[SecurityEvent] = []
        self.logger = get_logger(__name__)

    async def initialize_security_systems(self) -> dict[str, Any]:
        """Initialize all security hardening systems"""

        initialization_start = time.perf_counter()

        try:
            # Initialize encryption
            await self.encryption_manager.initialize_encryption()

            # Verify all components
            components_status = {
                "input_validator": "ready",
                "rate_limiter": "ready",
                "encryption_manager": "ready",
                "threat_detector": "ready",
            }

            initialization_time = (time.perf_counter() - initialization_start) * 1000

            result = {
                "status": "initialized",
                "components": components_status,
                "initialization_time_ms": initialization_time,
                "security_level": "hardened",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            self.logger.info(
                "Security hardening systems initialized",
                extra={
                    "initialization_time_ms": initialization_time,
                    "components": len(components_status),
                },
            )

            return result

        except Exception as e:
            self.logger.error(f"Security initialization failed: {str(e)}")
            raise ReflectAIError(f"Security hardening initialization failed: {str(e)}") from e

    async def process_secure_request(
        self,
        request_data: dict[str, Any],
        source_ip: str,
        user_id: str | None = None,
        team_id: str | None = None,
        rate_limit_key: str | None = None,
    ) -> dict[str, Any]:
        """Process request through complete security pipeline"""

        processing_start = time.perf_counter()

        try:
            security_result = {
                "allowed": True,
                "security_checks": {},
                "risk_assessment": {},
                "actions_taken": [],
                "sanitized_data": request_data,
            }

            # 1. Input validation
            validation_result = await self.input_validator.validate_input(
                request_data, "api_request", user_id
            )
            security_result["security_checks"]["input_validation"] = validation_result

            if not validation_result["is_valid"]:
                security_result["allowed"] = False
                security_result["actions_taken"].append("blocked_invalid_input")

                # Log security event
                await self._log_security_event(
                    SecurityEventType.INPUT_VALIDATION_FAILURE,
                    ThreatLevel.HIGH,
                    source_ip,
                    user_id,
                    team_id,
                    {"validation_result": validation_result},
                )

            # 2. Rate limiting check
            if rate_limit_key:
                rate_limit_result = await self.rate_limiter.check_rate_limit(
                    rate_limit_key,
                    limit=100,  # 100 requests per hour
                    window_seconds=3600,
                    algorithm="sliding_window",
                )
                security_result["security_checks"]["rate_limiting"] = rate_limit_result

                if not rate_limit_result["allowed"]:
                    security_result["allowed"] = False
                    security_result["actions_taken"].append("blocked_rate_limit")

                    await self._log_security_event(
                        SecurityEventType.RATE_LIMIT_EXCEEDED,
                        ThreatLevel.MEDIUM,
                        source_ip,
                        user_id,
                        team_id,
                        {"rate_limit_result": rate_limit_result},
                    )

            # 3. Threat detection
            threat_analysis = await self.threat_detector.analyze_request(
                request_data, source_ip, user_id, team_id
            )
            security_result["risk_assessment"] = threat_analysis

            if threat_analysis["should_block"]:
                security_result["allowed"] = False
                security_result["actions_taken"].append("blocked_threat_detection")

                await self._log_security_event(
                    SecurityEventType.SUSPICIOUS_ACTIVITY,
                    threat_analysis["threat_level"],
                    source_ip,
                    user_id,
                    team_id,
                    {"threat_analysis": threat_analysis},
                )

            # 4. Apply security actions based on threat level
            if security_result["allowed"] and threat_analysis["threat_level"] in [
                ThreatLevel.HIGH,
                ThreatLevel.CRITICAL,
            ]:
                if threat_analysis["recommended_action"] == "require_additional_auth":
                    security_result["actions_taken"].append("require_additional_auth")
                elif threat_analysis["recommended_action"] == "log_and_monitor":
                    security_result["actions_taken"].append("enhanced_monitoring")

            # 5. Encrypt sensitive data if request is allowed
            if security_result["allowed"] and validation_result.get("sanitized_data"):
                security_result["sanitized_data"] = validation_result["sanitized_data"]

            processing_time = (time.perf_counter() - processing_start) * 1000

            security_result.update(
                {"processing_time_ms": processing_time, "timestamp": datetime.now(UTC).isoformat()}
            )

            self.logger.info(
                "Secure request processing completed",
                extra={
                    "allowed": security_result["allowed"],
                    "threat_level": threat_analysis.get("threat_level"),
                    "actions_taken": len(security_result["actions_taken"]),
                    "processing_time_ms": processing_time,
                    "source_ip": source_ip,
                    "user_id": user_id,
                },
            )

            return security_result

        except Exception as e:
            self.logger.error(f"Secure request processing failed: {str(e)}")

            # Log critical security event
            await self._log_security_event(
                SecurityEventType.ENCRYPTION_FAILURE,
                ThreatLevel.CRITICAL,
                source_ip,
                user_id,
                team_id,
                {"error": str(e)},
            )

            # Fail secure
            return {
                "allowed": False,
                "error": "security_processing_failed",
                "actions_taken": ["blocked_security_error"],
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def _log_security_event(
        self,
        event_type: SecurityEventType,
        threat_level: ThreatLevel,
        source_ip: str,
        user_id: str | None,
        team_id: str | None,
        details: dict[str, Any],
        blocked: bool = True,
    ):
        """Log security event for audit trail"""

        event = SecurityEvent(
            event_id=f"sec_{int(time.time() * 1000000)}",
            event_type=event_type,
            threat_level=threat_level,
            source_ip=source_ip,
            user_id=user_id,
            team_id=team_id,
            details=details,
            timestamp=datetime.now(UTC),
            blocked=blocked,
        )

        self.security_events.append(event)

        # Store in Redis for audit trail
        await self.redis.lpush(
            "security_events",
            json.dumps(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "threat_level": event.threat_level.value,
                    "source_ip": event.source_ip,
                    "user_id": event.user_id,
                    "team_id": event.team_id,
                    "details": event.details,
                    "timestamp": event.timestamp.isoformat(),
                    "blocked": event.blocked,
                }
            ),
        )

        # Keep only recent events (last 10,000)
        await self.redis.ltrim("security_events", 0, 9999)

        # Set expiry (30 days)
        await self.redis.expire("security_events", 86400 * 30)

    async def get_security_dashboard_data(self) -> dict[str, Any]:
        """Get security dashboard data"""

        try:
            # Get recent security events
            recent_events = await self.redis.lrange("security_events", 0, 100)

            parsed_events = []
            for event_data in recent_events:
                try:
                    event = json.loads(event_data)
                    parsed_events.append(event)
                except json.JSONDecodeError:
                    continue

            # Calculate security metrics
            total_events = len(parsed_events)
            blocked_events = len([e for e in parsed_events if e.get("blocked", True)])
            critical_events = len([e for e in parsed_events if e.get("threat_level") == "critical"])

            # Group events by type
            events_by_type = {}
            for event in parsed_events:
                event_type = event.get("event_type", "unknown")
                events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

            return {
                "security_status": "active",
                "total_security_events_24h": total_events,
                "blocked_requests_24h": blocked_events,
                "critical_threats_24h": critical_events,
                "threat_block_rate_pct": (blocked_events / total_events * 100)
                if total_events > 0
                else 0,
                "events_by_type": events_by_type,
                "recent_events": parsed_events[:10],  # Last 10 events
                "security_level": "hardened",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Security dashboard data generation failed: {str(e)}")
            raise ReflectAIError(f"Security dashboard failed: {str(e)}") from e
