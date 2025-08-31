import pytest
from django.apps import apps

pytestmark = pytest.mark.django_db

def test_models_importable():
    assert apps.all_models
