# analytics/selectors/product_inventory.py
from django.db.models import Sum, Value, IntegerField
from django.db.models.functions import Coalesce

from ..utils.model_helpers import get_model  # sizda allaqachon bor

def compute_product_inventory_stats(store_id=None):
    """
    Qaytaradi:
      products_total_objects       - Mahsulotlar soni (obyektlar)
      products_total_qty           - Mahsulotlarning umumiy soni (shelf + warehouse)
      warehouse_product_types      - Ombordagi mahsulot turlarining soni (warehouse_count > 0)
      warehouse_total_qty          - Ombordagi mahsulotlar umumiy soni (Σ warehouse_count)
    """
    Product = get_model('Product')
    if not Product:
        return {
            'products_total_objects': 0,
            'products_total_qty': 0,
            'warehouse_product_types': 0,
            'warehouse_total_qty': 0,
        }, 'none'

    qs = Product.objects.filter(is_deleted=False)
    if store_id:
        qs = qs.filter(store_id=store_id)

    # 1) Mahsulotlar soni (obyektlar)
    products_total_objects = qs.count()

    # 2) Ombordagi turlar va ombor miqdori
    warehouse_product_types = qs.filter(warehouse_count__gt=0).count()
    warehouse_total_qty = qs.aggregate(
        v=Coalesce(Sum('warehouse_count', output_field=IntegerField()), Value(0))
    )['v'] or 0

    # 3) Umumiy miqdor (shelf + warehouse)
    shelf_total_qty = qs.aggregate(
        v=Coalesce(Sum('count', output_field=IntegerField()), Value(0))
    )['v'] or 0
    products_total_qty = (shelf_total_qty or 0) + (warehouse_total_qty or 0)

    return {
        'products_total_objects': products_total_objects,
        'products_total_qty': products_total_qty,
        'warehouse_product_types': warehouse_product_types,
        'warehouse_total_qty': warehouse_total_qty,
    }, "Product(count, warehouse_count)"
