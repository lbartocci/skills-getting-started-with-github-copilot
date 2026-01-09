"""
Test suite for Mergington High School Activity Management API
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient
from app import app

# Create a test client
client = TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    from app import activities
    # Store original state
    original_activities = {
        "Basketball Team": {
            "description": "Join our competitive basketball team and play in league games",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": ["james@mergington.edu"]
        },
        "Tennis Club": {
            "description": "Practice tennis skills and compete in matches",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:00 PM",
            "max_participants": 10,
            "participants": ["sarah@mergington.edu"]
        },
        "Drama Club": {
            "description": "Perform in theatrical productions and develop acting skills",
            "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 25,
            "participants": ["lucas@mergington.edu", "mia@mergington.edu"]
        },
    }
    
    # Clear and restore
    activities.clear()
    activities.update(original_activities)
    yield
    # Cleanup
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Test suite for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Basketball Team" in data
    
    def test_get_activities_contains_required_fields(self):
        """Test that activities contain required fields"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Basketball Team"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
    
    def test_get_activities_participants_is_list(self):
        """Test that participants field is a list"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert isinstance(activity["participants"], list)


class TestSignup:
    """Test suite for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
    
    def test_signup_for_activity_updates_participants(self, reset_activities):
        """Test that signup actually adds participant to activity"""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Basketball Team/signup?email={email}")
        
        response = client.get("/activities")
        activity = response.json()["Basketball Team"]
        assert email in activity["participants"]
    
    def test_signup_for_nonexistent_activity(self, reset_activities):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/NonExistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_duplicate_student(self, reset_activities):
        """Test that duplicate signup is rejected"""
        # First signup
        response1 = client.post(
            "/activities/Basketball Team/signup?email=test@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Try to signup again
        response2 = client.post(
            "/activities/Basketball Team/signup?email=test@mergington.edu"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_already_registered_student(self, reset_activities):
        """Test that already registered student cannot sign up again"""
        # james@mergington.edu is already registered for Basketball Team
        response = client.post(
            "/activities/Basketball Team/signup?email=james@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]


class TestUnregister:
    """Test suite for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, reset_activities):
        """Test successful unregister from activity"""
        # First signup
        client.post("/activities/Basketball Team/signup?email=test@mergington.edu")
        
        # Then unregister
        response = client.delete(
            "/activities/Basketball Team/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, reset_activities):
        """Test that unregister actually removes participant"""
        email = "test@mergington.edu"
        
        # Signup
        client.post(f"/activities/Basketball Team/signup?email={email}")
        
        # Unregister
        client.delete(f"/activities/Basketball Team/unregister?email={email}")
        
        # Verify removed
        response = client.get("/activities")
        activity = response.json()["Basketball Team"]
        assert email not in activity["participants"]
    
    def test_unregister_nonexistent_activity(self, reset_activities):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/NonExistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_unregister_not_registered_student(self, reset_activities):
        """Test unregister for student not in activity returns 400"""
        response = client.delete(
            "/activities/Basketball Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_existing_participant(self, reset_activities):
        """Test unregister of existing participant works"""
        # james@mergington.edu is already registered for Basketball Team
        response = client.delete(
            "/activities/Basketball Team/unregister?email=james@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify removed
        response = client.get("/activities")
        activity = response.json()["Basketball Team"]
        assert "james@mergington.edu" not in activity["participants"]


class TestIntegration:
    """Integration tests for multiple operations"""
    
    def test_full_signup_unregister_workflow(self, reset_activities):
        """Test complete workflow of signup and unregister"""
        email = "integration@mergington.edu"
        activity = "Basketball Team"
        
        # Verify not signed up initially
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signed up
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistered
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
    
    def test_multiple_signups_different_activities(self, reset_activities):
        """Test student can signup for multiple activities"""
        email = "multisignup@mergington.edu"
        
        # Signup for multiple activities
        response1 = client.post(
            f"/activities/Basketball Team/signup?email={email}"
        )
        response2 = client.post(
            f"/activities/Tennis Club/signup?email={email}"
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify in both
        response = client.get("/activities")
        activities_data = response.json()
        assert email in activities_data["Basketball Team"]["participants"]
        assert email in activities_data["Tennis Club"]["participants"]
