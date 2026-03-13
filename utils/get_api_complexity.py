from utils.logger import get_logger
logger = get_logger(__name__)
def get_api_complexity(endpoint):
    """Get the complexity level of an API endpoint.

    Args:
        endpoint: API endpoint path (e.g., "/auth/login", "/auth/me", "/users")

    Returns:
        str: Complexity level ("small", "medium", "complex"), defaults to "medium" if not found
    """
    # Mapping of endpoints to API classes
    endpoint_to_api = {
        "/auth/login": ("api.auth_api", "AuthAPI"),
        "/auth/me": ("api.user_api", "UserAPI"),
        "/users": ("api.user_api", "UserAPI"),
    }
    logger.debug(f"DEBUG endpoint received: repr={repr(endpoint)}")

    if endpoint not in endpoint_to_api:
        logger.warning(f"⚠️  No API class found for endpoint {endpoint}, defaulting to 'medium' complexity")
        return "medium"

    try:
        module_name, class_name = endpoint_to_api[endpoint]
        module = __import__(module_name, fromlist=[class_name])
        api_class = getattr(module, class_name)
        complexity = getattr(api_class, "complexity", "medium")
        return complexity
    except Exception as e:
        logger.error(f"❌ Error loading complexity for {endpoint}: {e}")
        return "medium"
