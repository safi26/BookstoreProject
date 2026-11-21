import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookstore", "0027_staffcartitempricechange"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="voucher_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="sale",
            name="voucher_code",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AlterField(
            model_name="sale",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("cash", "Cash"),
                    ("card", "Card (demo)"),
                    ("voucher", "Voucher"),
                ],
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name="Voucher",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("voucher_id", models.CharField(max_length=30, unique=True)),
                (
                    "balance",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Voucher",
                "verbose_name_plural": "Vouchers",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("balance__gte", 0)),
                        name="voucher_balance_not_negative",
                    )
                ],
            },
        ),
    ]
