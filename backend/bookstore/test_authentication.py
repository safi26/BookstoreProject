from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from .models import Category


class TokenAuthenticationApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="token-student",
            password="student-password",
        )
        self.manager_group, _ = Group.objects.get_or_create(name="Manager")
        self.manager = get_user_model().objects.create_user(
            username="token-manager",
            password="manager-password",
        )
        self.manager.groups.add(self.manager_group)

    def test_login_verifies_password_and_returns_server_derived_role(self):
        response = self.client.post(
            "/api/auth/login/",
            {"user_id": self.user.pk, "password": "student-password"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user_id"], self.user.pk)
        self.assertEqual(response.data["role"], "Student")
        self.assertTrue(response.data["token"])

    def test_login_rejects_invalid_password(self):
        response = self.client.post(
            "/api/auth/login/",
            {"user_id": self.user.pk, "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("token", response.data)

    def test_manager_role_comes_from_django_group_not_request_data(self):
        response = self.client.post(
            "/api/auth/login/",
            {
                "user_id": self.user.pk,
                "password": "student-password",
                "role": "Manager",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "Student")

    def test_manager_token_can_write_and_student_token_cannot(self):
        category = Category.objects.create(category_name="Token authorization")
        student_token = self.client.post(
            "/api/auth/login/",
            {"user_id": self.user.pk, "password": "student-password"},
            format="json",
        ).data["token"]
        manager_token = self.client.post(
            "/api/auth/login/",
            {"user_id": self.manager.pk, "password": "manager-password"},
            format="json",
        ).data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {student_token}")
        denied = self.client.patch(
            f"/api/categories/{category.pk}/",
            {"discount_type": "percent", "discount_value": "10.00"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {manager_token}")
        allowed = self.client.patch(
            f"/api/categories/{category.pk}/",
            {"discount_type": "percent", "discount_value": "10.00"},
            format="json",
        )
        self.assertEqual(allowed.status_code, 200)

    def test_logout_revokes_token(self):
        token = self.client.post(
            "/api/auth/login/",
            {"user_id": self.user.pk, "password": "student-password"},
            format="json",
        ).data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        logout = self.client.post("/api/auth/logout/")
        protected = self.client.get(f"/api/users/{self.user.pk}/cart/")

        self.assertEqual(logout.status_code, 204)
        self.assertEqual(protected.status_code, 401)
