
from decimal import Decimal
from django.apps import apps
from django.core.exceptions import FieldError
from django.db.models import DateField, DateTimeField

D0 = Decimal('0')


def get_model(name: str):
    for m in apps.get_models():
        if m.__name__ == name:
            return m
    return None


def find_field(model, candidates):
    if not model:
        return None
    names = {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}
    for c in candidates:
        if c in names:
            return c
    return None


def date_range_kwargs(Model, start_dt, end_dt):
    if not Model:
        return {}
    fields = {f.name: f for f in Model._meta.get_fields() if hasattr(f, "attname")}
    for cand in ("created_at", "date", "created", "datetime", "timestamp", "created_on"):
        f = fields.get(cand)
        if f:
            if isinstance(f, DateField) and not isinstance(f, DateTimeField):
                return {f"{cand}__range": (start_dt.date(), end_dt.date())}
            return {f"{cand}__range": (start_dt, end_dt)}
    return {}


def try_filter_store(qs, store_id, candidates):
    if not store_id:
        return qs
    for path in candidates:
        try:
            return qs.filter(**{path: store_id})
        except FieldError:
            continue
    return qs

