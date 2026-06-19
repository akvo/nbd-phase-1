import logging
from typing import Dict, Type, Optional
from app.models.form import FormType
from app.services.scoring.base import BaseScoringHandler

logger = logging.getLogger(__name__)

_registry: Dict[FormType, Type[BaseScoringHandler]] = {}


def register_handler(form_type: FormType):
    """Decorator to register a scoring handler for a specific FormType."""

    def decorator(cls: Type[BaseScoringHandler]):
        _registry[form_type] = cls
        logger.info(
            "Registered scoring handler %s for FormType %s",
            cls.__name__,
            form_type,
        )
        return cls

    return decorator


def get_handler(form_type: FormType) -> Optional[Type[BaseScoringHandler]]:
    """Retrieves the registered scoring handler class for a given FormType."""
    return _registry.get(form_type)
