# Export base registry utilities
from app.services.scoring.registry import (  # noqa: F401
    register_handler,  # noqa: F401
    get_handler,  # noqa: F401
)

# Import individual handler modules to ensure their decorators run
import app.services.scoring.handlers.wetland  # noqa: F401
