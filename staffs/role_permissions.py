ROLE_PERMISSIONS = {
    "manager": {
        "storestaff": ["create", "retrieve", "update", "delete", "list"],
        "cashbox": ["retrieve", "list"],
        "order": ["create", "retrieve", "update", "delete", "list"],
        "productorder": ["create", "retrieve", "update", "delete", "list"],
        "product": ["create", "retrieve", "update", "delete", "list"],
        "stockentry": ["create", "retrieve", "update", "delete", "list"],
        "stocktransfer": ["create", "retrieve", "update", "delete", "list"],
        "productsale": ["create", "retrieve", "update", "delete", "list"],
        "productentrysystem": ["create", "retrieve", "update", "delete", "list"],
        "productimage": ["create", "retrieve", "update", "delete", "list"],
        "properties": ["create", "retrieve", "update", "delete", "list"],
        "expense": ["create", "retrieve", "update", "delete", "list"],
    },
    "seller": {
        "product": ["create", "retrieve", "update", "list"],
        "order": ["create", "retrieve", "update", "list"],
        "rate": ["retrieve", "list"],
        "cashbox": ["retrieve"],
        "store": ["retrieve"],
        "productimage": ["create", "list"],
        "platformuser": ["retrieve"],
        "productsale": ["retrieve", "list"],
    },
    "cashier": {
        "order": ["create", "retrieve", "list"],
        "cashbox": ["create", "retrieve", "list"],
        "rate": ["retrieve"],
        "productsale": ["retrieve", "list"],
        "expense": ["create", "retrieve", "list"],
    },
    "stockman": {
        "product": ["retrieve", "update", "list"],
        "stockentry": ["create", "retrieve", "list"],
        "stocktransfer": ["create", "retrieve", "list"],
        "productentrysystem": ["create", "retrieve", "list"],
        "cashbox": ["retrieve"],
    },
    "deliverer": {
        "order": ["retrieve", "list"],
    },
    "viewer": {
        "product": ["retrieve", "list"],
        "order": ["retrieve", "list"],
        "rate": ["retrieve"],
        "store": ["retrieve"],
        "platformuser": ["retrieve", "list"],
        "productsale": ["retrieve", "list"],
        "stocktransfer": ["retrieve", "list"],
        "productentrysystem": ["retrieve", "list"],
    },
}
ACTION_MAP = {
    "list": "list",
    "retrieve": "retrieve",
    "create": "create",
    "update": "update",
    "partial_update": "update",
    "destroy": "delete",

    # products actions
    "stock_entries": "retrieve",
    "add_stock_entry": "create",
    "get_properties": "retrieve",
    "add_property": "create",
    "get_images": "retrieve",
    "add_images": "create",

    # order actions
    "get_order_items": "retrieve",

    # trash actions
    "restore": "update",
    "hard_delete": "delete",
}
