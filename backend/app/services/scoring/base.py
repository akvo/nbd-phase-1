from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from app.models.submission import Datapoint


class BaseScoringHandler(ABC):
    @classmethod
    @abstractmethod
    def score_submission(cls, db: Session, datapoint: Datapoint) -> None:
        """Processes the approved datapoint and generates scoring records."""
        pass
