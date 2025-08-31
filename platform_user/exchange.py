from decimal import Decimal
from platform_user.models import PlatformUser, RateUsd

def get_default_exchange_rate(user):
    try:
        platform_user = user.platform_profile
    except PlatformUser.DoesNotExist:
        return Decimal("1.0")

    if platform_user.chief:
        try:
            return platform_user.chief.usd_rate.rate
        except RateUsd.DoesNotExist:
            pass

    try:
        return platform_user.usd_rate.rate
    except RateUsd.DoesNotExist:
        return Decimal("1.0")