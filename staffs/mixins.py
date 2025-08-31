from store.models import Store
from rest_framework.exceptions import NotFound

class StoreIDMixin:
    def get_store_id(self):
        store_id = self.kwargs.get('store_id')
        if not store_id:
            raise NotFound("store_id URLda mavjud emas.")
        return store_id

    def get_store(self):
        try:
            return Store.objects.get(id=self.get_store_id())
        except Store.DoesNotExist:
            raise NotFound("Berilgan store mavjud emas.")
