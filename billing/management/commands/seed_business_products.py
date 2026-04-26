from django.core.management.base import BaseCommand

from billing.models import Entitlement, Plan, Price, Project
from business_rules.catalog import BUSINESS_PRODUCTS


def entitlement_value_fields(value):
    if isinstance(value, bool):
        return {"value_type": Entitlement.ValueType.BOOLEAN, "bool_value": value, "int_value": None, "str_value": ""}
    if isinstance(value, int):
        return {"value_type": Entitlement.ValueType.INTEGER, "bool_value": False, "int_value": value, "str_value": ""}
    return {"value_type": Entitlement.ValueType.STRING, "bool_value": False, "int_value": None, "str_value": str(value)}


class Command(BaseCommand):
    help = "Seed product, plan, price, and entitlement defaults for ZATCA, typing, chat, and blog."

    def handle(self, *args, **options):
        created_projects = created_plans = created_prices = created_entitlements = 0
        for code, data in BUSINESS_PRODUCTS.items():
            project, created = Project.objects.update_or_create(
                code=code,
                defaults={"name": data["name"], "description": data["description"], "is_active": True},
            )
            created_projects += int(created)
            for plan_code, plan_data in data["plans"].items():
                plan, created = Plan.objects.update_or_create(
                    code=plan_code,
                    defaults={
                        "project": project,
                        "name": plan_data["name"],
                        "visibility": Plan.Visibility.PUBLIC,
                        "is_active": True,
                        "metadata": {"business_core": True, "product": code},
                    },
                )
                created_plans += int(created)
                price_cents = int(plan_data["price_cents"])
                interval = Price.Interval.MONTH if price_cents else Price.Interval.ONE_TIME
                _, created = Price.objects.update_or_create(
                    code=f"{plan_code}-usd-monthly" if price_cents else f"{plan_code}-free",
                    defaults={
                        "plan": plan,
                        "currency": "USD",
                        "amount_cents": price_cents,
                        "interval": interval,
                        "is_active": True,
                        "metadata": {"business_core": True, "product": code},
                    },
                )
                created_prices += int(created)
                for key, value in plan_data["entitlements"].items():
                    defaults = entitlement_value_fields(value)
                    defaults["metadata"] = {"business_core": True, "product": code}
                    _, created = Entitlement.objects.update_or_create(plan=plan, key=key, defaults=defaults)
                    created_entitlements += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded business products: projects={created_projects}, plans={created_plans}, prices={created_prices}, entitlements={created_entitlements}"
        ))
