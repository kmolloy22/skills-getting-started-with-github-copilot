import copy
import pytest
from fastapi.testclient import TestClient

from src.app import app, activities as app_activities


@pytest.fixture(autouse=True)
def reset_state():
    """Backup and restore in-memory activities between tests to avoid cross-test pollution."""
    backup = copy.deepcopy(app_activities)
    try:
        yield
    finally:
        app_activities.clear()
        app_activities.update(copy.deepcopy(backup))


@pytest.fixture()
def client():
    return TestClient(app)


def test_get_activities_returns_expected_structure(client):
    resp = client.get("/activities")
    assert resp.status_code == 200
    data = resp.json()
    # Has several known activities
    assert isinstance(data, dict)
    assert "Chess Club" in data
    assert "Programming Class" in data
    # Each activity has required fields
    for details in data.values():
        assert set(["description", "schedule", "max_participants", "participants"]).issubset(details.keys())


def test_signup_success_and_reflected_in_listing(client):
    activity = "Gym Class"
    email = "newstudent@mergington.edu"

    # Ensure not present initially
    before = client.get("/activities").json()[activity]["participants"]
    assert email not in before

    # Sign up
    resp = client.post(f"/activities/{activity}/signup", params={"email": email})
    assert resp.status_code == 200
    assert "Signed up" in resp.json()["message"]

    # Now present
    after = client.get("/activities").json()[activity]["participants"]
    assert email in after


def test_signup_duplicate_is_rejected(client):
    activity = "Programming Class"
    existing_email = "emma@mergington.edu"  # already registered in seed data

    resp = client.post(f"/activities/{activity}/signup", params={"email": existing_email})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Student is already signed up"


def test_unregister_success_then_cannot_unregister_twice(client):
    activity = "Art Club"
    email = "isabella@mergington.edu"  # present in seed data

    # Unregister succeeds first time
    resp = client.delete(f"/activities/{activity}/unregister", params={"email": email})
    assert resp.status_code == 200
    assert "Unregistered" in resp.json()["message"]

    # No longer in list
    participants = client.get("/activities").json()[activity]["participants"]
    assert email not in participants

    # Second attempt should be rejected
    resp2 = client.delete(f"/activities/{activity}/unregister", params={"email": email})
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "Student is not registered for this activity"


def test_activity_not_found_404(client):
    missing = "Underwater Basket Weaving"
    email = "nobody@mergington.edu"

    r1 = client.post(f"/activities/{missing}/signup", params={"email": email})
    assert r1.status_code == 404
    assert r1.json()["detail"] == "Activity not found"

    r2 = client.delete(f"/activities/{missing}/unregister", params={"email": email})
    assert r2.status_code == 404
    assert r2.json()["detail"] == "Activity not found"
