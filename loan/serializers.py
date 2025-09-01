from rest_framework import serializers
from .models import DebtUser, DebtDocument, DocumentProduct, DebtImportOffer


class DebtImportOfferCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtImportOffer
        fields = ["id", "debtor_user", "payload", "expires_at", "idempotency_key"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        payload = attrs.get("payload") or {}
        if "amount" not in payload:
            raise serializers.ValidationError({"payload.amount": "required"})
        return attrs


class DebtImportOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtImportOffer
        fields = "__all__"


class DebtImportOfferAcceptSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()


class DebtImportOfferRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

class DebtUserMessageSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        max_length=15, help_text="DebtUser’s phone number"
    )
    title = serializers.CharField(max_length=255, help_text="Notification title")
    description = serializers.CharField(help_text="Message body")
    action = serializers.CharField(
        max_length=50, help_text="Client-side action (e.g. 'copy', 'share')"
    )


class DocumentProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentProduct
        fields = '__all__'
        read_only_fields = ['amount', 'amount_usd', 'document']


class DebtDocumentSerializer(serializers.ModelSerializer):
    products = DocumentProductSerializer(many=True, required=False)

    class Meta:
        model = DebtDocument
        fields = '__all__'
        read_only_fields = ['product_amount', 'total_amount', 'is_deleted', 'deleted_at']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        if user and 'owner' not in validated_data:
            validated_data['owner'] = user

        phone = validated_data.pop('phone_number', None)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        store = validated_data.get('store')

        if phone and store:
            debtuser, _ = DebtUser.objects.get_or_create(
                phone_number=phone,
                store=store,
                defaults={'first_name': first_name, 'last_name': last_name}
            )
            validated_data['debtuser'] = debtuser

        # 🟢 Bu yerga yozamiz, modelning o‘zida saqlansin deb
        validated_data['phone_number'] = phone
        validated_data['first_name'] = first_name
        validated_data['last_name'] = last_name

        products_data = validated_data.pop('products', [])
        document = DebtDocument.objects.create(**validated_data)

        for product_data in products_data:
            DocumentProduct.objects.create(document=document, **product_data)

        document.debtuser.recalculate_balance()
        return document

    def update(self, instance, validated_data):
        products_data = validated_data.pop('products', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if products_data is not None:
            instance.products.all().delete()
            for product_data in products_data:
                DocumentProduct.objects.create(document=instance, **product_data)

        # 💡 Balans yangilanishi uchun:
        instance.debtuser.recalculate_balance()
        return instance



class DebtUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtUser
        fields = '__all__'
        read_only_fields = [
            'store',
            'transferred', 'accepted', 'balance',
            'is_deleted', 'deleted_at',  # <-- YANGI
        ]

    def create(self, validated_data):
        view = self.context.get('view')
        store_id = view.kwargs.get('store_id') if view else None
        if not store_id:
            raise serializers.ValidationError({'store': 'Store ID not provided in URL.'})
        validated_data['store_id'] = store_id
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('store', None)
        validated_data.pop('store_id', None)
        return super().update(instance, validated_data)