import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_create_user_with_phone_number():
    user = User.objects.create_user(
        username="john_doe",
        password="secure1234",
        phone_number="+998901234567"
    )
    assert user.phone_number == "+998901234567"
    assert user.username == "john_doe"
    assert user.check_password("secure1234") is True

@pytest.mark.django_db
def test_user_str_returns_full_name_or_username():
    user = User.objects.create_user(
        username="jane_doe",
        first_name="Jane",
        last_name="Doe",
        phone_number="+998991234567"
    )
    result = str(user)
    assert result == "Jane Doe" or result == "jane_doe"

@pytest.mark.django_db
def test_gender_choices_available():
    assert User.Gender.MALE == "male"
    assert User.Gender.FEMALE == "female"