from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum, Q
from accounts.models import Distributor
from catalog.models import StockLevel, StockMovement


class Command(BaseCommand):
    help = 'Reconcile stock levels against movement ledger. Reports discrepancies and exits with code 1 if any drift found.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--distributor',
            type=int,
            help='Distributor ID to reconcile (all if omitted)',
        )

    def handle(self, *args, **options):
        distributor_id = options.get('distributor')

        if distributor_id:
            try:
                distributor = Distributor.objects.get(id=distributor_id)
            except Distributor.DoesNotExist:
                raise CommandError(f'Distributor {distributor_id} not found.')
            stock_levels = StockLevel.objects.filter(product__distributor=distributor)
        else:
            stock_levels = StockLevel.objects.all()

        discrepancies = []

        for stock in stock_levels:
            ledger_sum = StockMovement.objects.filter(
                product=stock.product,
                warehouse=stock.warehouse,
            ).aggregate(total=Sum('delta'))['total'] or 0

            if ledger_sum != stock.quantity:
                discrepancies.append({
                    'product': stock.product.name,
                    'product_id': stock.product.id,
                    'warehouse': stock.warehouse.name,
                    'sku': stock.product.sku,
                    'recorded_qty': stock.quantity,
                    'ledger_sum': ledger_sum,
                    'drift': ledger_sum - stock.quantity,
                })

        if discrepancies:
            self.stdout.write(self.style.ERROR(f'\nFound {len(discrepancies)} discrepancy(ies):\n'))
            for disc in discrepancies:
                self.stdout.write(
                    self.style.ERROR(
                        f"  {disc['product']} ({disc['sku']}) @ {disc['warehouse']}: "
                        f"recorded {disc['recorded_qty']}, ledger sum {disc['ledger_sum']} "
                        f"(drift: {disc['drift']:+d})"
                    )
                )
            self.stdout.write(self.style.ERROR(''))
            exit(1)
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ All stock levels reconciled successfully (no discrepancies).')
            )
