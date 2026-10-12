"""FastAPI 의존성. 테스트에서는 app.dependency_overrides 로 메모리 저장소로 교체한다."""
from app.core.firebase import get_firestore
from app.repositories.firestore import FirestoreConversationRepository, FirestoreDataRepository


def get_data_repo():
    return FirestoreDataRepository(get_firestore())


def get_conversation_repo():
    return FirestoreConversationRepository(get_firestore())
