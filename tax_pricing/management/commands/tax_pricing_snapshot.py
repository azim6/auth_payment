from django.core.management.base import BaseCommand
from tax_pricing.models import Currency, Region, RegionalPrice, TaxJurisdiction


class Command(BaseCommand):
    help = "Print a tax/pricing configuration snapshot for release checks."

    def handle(self, *args, **options):
        self.stdout.write(f"currencies={Currency.objects.count()}")
        self.stdout.write(f"regions={Region.objects.count()}")
        self.stdout.write(f"regional_prices={RegionalPrice.objects.count()}")
        self.stdout.write(f"tax_jurisdictions={TaxJurisdiction.objects.count()}")
