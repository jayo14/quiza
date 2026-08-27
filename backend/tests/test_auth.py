def test_signup_returns_user_and_tokens(client):
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "a@example.com", "password": "password123", "name": "A"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "a@example.com"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]


def test_signup_duplicate_email_is_rejected(client):
    payload = {"email": "dupe@example.com", "password": "password123", "name": "A"}
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 409


def test_signin_with_wrong_password_is_rejected(client, signup):
    signup(email="b@example.com", password="password123")
    response = client.post(
        "/api/v1/auth/signin", json={"email": "b@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, signup):
    headers, user = signup(email="c@example.com")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]


def test_forgot_and_reset_password_flow(client, signup):
    signup(email="d@example.com", password="oldpassword1")

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "d@example.com"})
    assert forgot.status_code == 200
    reset_token = forgot.json()["reset_token"]
    assert reset_token

    reset = client.post(
        "/api/v1/auth/reset-password", json={"token": reset_token, "new_password": "newpassword1"}
    )
    assert reset.status_code == 204

    old_login = client.post("/api/v1/auth/signin", json={"email": "d@example.com", "password": "oldpassword1"})
    assert old_login.status_code == 401

    new_login = client.post("/api/v1/auth/signin", json={"email": "d@example.com", "password": "newpassword1"})
    assert new_login.status_code == 200


def test_forgot_password_does_not_reveal_whether_email_exists(client):
    response = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert response.json()["reset_token"] is None
