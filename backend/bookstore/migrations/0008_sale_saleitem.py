import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("bookstore", "0007_use_categories_for_shelves"),
    ]

    operations = [
        migrations.CreateModel(
            name="Sale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("receipt_number", models.CharField(max_length=32, unique=True)),
                ("payment_method", models.CharField(choices=[("cash", "Cash"), ("card", "Card (demo)")], max_length=10)),
                ("total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("cash_received", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("change_due", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bookstore_sales", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="SaleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item_name", models.CharField(max_length=200)),
                ("item_code", models.CharField(blank=True, default="", max_length=30)),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sale_items", to="bookstore.item")),
                ("sale", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sale_items", to="bookstore.sale")),
            ],
        ),
    ]