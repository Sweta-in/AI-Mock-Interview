"""
PrepAI — Integration tests for interview router.
Tests create, start, and abandon interview endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


# We need to mock dependencies before importing the app
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock external dependencies for testing."""
    with patch("apps.api.db.postgres.init_db", new_callable=AsyncMock), \
         patch("apps.api.db.postgres.close_db", new_callable=AsyncMock), \
         patch("apps.api.db.mongo.connect_mongo", new_callable=AsyncMock), \
         patch("apps.api.db.mongo.close_mongo", new_callable=AsyncMock), \
         patch("apps.api.core.auth.close_redis", new_callable=AsyncMock), \
         patch("apps.api.db.mongo.create_transcript", new_callable=AsyncMock):
        yield


@pytest.fixture
def mock_user_context():
    """Create a mock authenticated user."""
    from apps.api.core.auth import UserContext
    return UserContext(
        id="550e8400-e29b-41d4-a716-446655440000",
        supabase_id="sub_123",
        email="test@example.com",
        full_name="Test User",
        plan="free",
        interviews_used_this_month=0,
    )


@pytest.fixture
def client(mock_user_context):
    """Create a test client with mocked auth."""
    with patch("apps.api.core.auth.get_current_user", return_value=mock_user_context):
        from apps.api.main import app
        return TestClient(app)


class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "prepai-api"


class TestInterviewRouter:
    @patch("apps.api.interview.service.get_role_by_slug")
    @patch("apps.api.interview.service.create_interview")
    @patch("apps.api.user.service.increment_interview_count", new_callable=AsyncMock)
    def test_create_interview_success(
        self, mock_increment, mock_create, mock_get_role, client
    ):
        """Test creating a new interview."""
        mock_role = MagicMock()
        mock_role.id = "role-uuid"
        mock_role.slug = "software-engineer-backend"
        mock_get_role.return_value = mock_role

        mock_interview = MagicMock()
        mock_interview.id = "interview-uuid"
        mock_interview.session_token = "test-token-abc"
        mock_interview.status = "created"
        mock_create.return_value = mock_interview

        response = client.post(
            "/api/v1/interviews",
            json={
                "role_slug": "software-engineer-backend",
                "difficulty": "medium",
                "interview_type": "mixed",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "created"
        assert "session_token" in data

    def test_create_interview_invalid_role(self, client):
        """Test creating with invalid role slug."""
        response = client.post(
            "/api/v1/interviews",
            json={
                "role_slug": "invalid slug!@#",
                "difficulty": "medium",
                "interview_type": "mixed",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 422  # Validation error

    def test_create_interview_plan_limit(self, client, mock_user_context):
        """Test plan limit enforcement (HTTP 402)."""
        mock_user_context.interviews_used_this_month = 5  # Over limit

        with patch("apps.api.core.auth.get_current_user", return_value=mock_user_context):
            from apps.api.main import app
            limited_client = TestClient(app)

            response = limited_client.post(
                "/api/v1/interviews",
                json={
                    "role_slug": "software-engineer-backend",
                    "difficulty": "medium",
                    "interview_type": "mixed",
                },
                headers={"Authorization": "Bearer test-token"},
            )
            assert response.status_code == 402

    @patch("apps.api.interview.service.get_interview")
    def test_get_interview_not_found(self, mock_get, client):
        """Test getting a non-existent interview."""
        mock_get.return_value = None

        response = client.get(
            "/api/v1/interviews/nonexistent-id",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 404

    @patch("apps.api.interview.service.get_interview")
    @patch("apps.api.interview.service.abandon_interview", new_callable=AsyncMock)
    def test_abandon_interview(self, mock_abandon, mock_get, client):
        """Test abandoning an active interview."""
        mock_interview = MagicMock()
        mock_interview.id = "interview-uuid"
        mock_interview.status = "active"
        mock_get.return_value = mock_interview

        response = client.post(
            "/api/v1/interviews/interview-uuid/abandon",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        assert "abandoned" in response.json()["message"].lower()

    @patch("apps.api.interview.service.get_interview")
    def test_abandon_completed_interview_fails(self, mock_get, client):
        """Cannot abandon a completed interview."""
        mock_interview = MagicMock()
        mock_interview.id = "interview-uuid"
        mock_interview.status = "completed"
        mock_get.return_value = mock_interview

        response = client.post(
            "/api/v1/interviews/interview-uuid/abandon",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 400
