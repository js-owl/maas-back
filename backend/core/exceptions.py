"""
Custom exception classes for the application
Provides consistent error handling across all modules
"""
from typing import Optional, Dict, Any


class BaseAPIException(Exception):
    """Base exception for all API-related errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(BaseAPIException):
    """Exception raised when a requested resource is not found"""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 404, "NOT_FOUND", details)


class ValidationException(BaseAPIException):
    """Exception raised when input validation fails"""
    
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 422, "VALIDATION_ERROR", details)


class AuthenticationException(BaseAPIException):
    """Exception raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 401, "AUTHENTICATION_ERROR", details)


class AuthorizationException(BaseAPIException):
    """Exception raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 403, "AUTHORIZATION_ERROR", details)


class ExternalServiceException(BaseAPIException):
    """Exception raised when external service calls fail"""
    
    def __init__(self, message: str = "External service error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 502, "EXTERNAL_SERVICE_ERROR", details)


class BitrixException(ExternalServiceException):
    """Exception raised when Bitrix integration fails"""
    
    def __init__(self, message: str = "Bitrix integration error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 502, "BITRIX_ERROR", details)


class DatabaseException(BaseAPIException):
    """Exception raised when database operations fail"""
    
    def __init__(self, message: str = "Database error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, "DATABASE_ERROR", details)


class FileProcessingException(BaseAPIException):
    """Exception raised when file processing fails"""
    
    def __init__(self, message: str = "File processing error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, "FILE_PROCESSING_ERROR", details)
