from decimal import Decimal

from django.db import migrations, models


SAMPLE_BOOKS = [
    {
        "item": "The Midnight Library",
        "author": "Matt Haig",
        "category": "Fiction",
        "catalog": "New & noteworthy",
        "item_code": "BK-0001",
        "item_price": Decimal("18.00"),
        "isbn": "9780525559474",
        "badge": "Book club pick",
        "item_quantity": 24,
    },
    {
        "item": "The Thursday Murder Club",
        "author": "Richard Osman",
        "category": "Mystery",
        "catalog": "Mystery shelf",
        "item_code": "BK-0002",
        "item_price": Decimal("17.50"),
        "isbn": "9781984880987",
        "badge": "Bestseller",
        "item_quantity": 18,
    },
    {
        "item": "A Psalm for the Wild-Built",
        "author": "Becky Chambers",
        "category": "Fantasy",
        "catalog": "Fantasy shelf",
        "item_code": "BK-0003",
        "item_price": Decimal("16.00"),
        "isbn": "9781250236210",
        "badge": "Staff pick",
        "item_quantity": 15,
    },
    {
        "item": "Braiding Sweetgrass",
        "author": "Robin Wall Kimmerer",
        "category": "Non-fiction",
        "catalog": "Non-fiction shelf",
        "item_code": "BK-0004",
        "item_price": Decimal("19.00"),
        "isbn": "9781571313560",
        "badge": "",
        "item_quantity": 12,
    },
    {
        "item": "The Very Secret Society of Irregular Witches",
        "author": "Sangu Mandanna",
        "category": "Fantasy",
        "catalog": "Fantasy shelf",
        "item_code": "BK-0005",
        "item_price": Decimal("18.00"),
        "isbn": "9780593439358",
        "badge": "Staff pick",
        "item_quantity": 14,
    },
    {
        "item": "The Creative Act",
        "author": "Rick Rubin",
        "category": "Non-fiction",
        "catalog": "New & noteworthy",
        "item_code": "BK-0006",
        "item_price": Decimal("24.00"),
        "isbn": "9780593652886",
        "badge": "A shop favorite",
        "item_quantity": 10,
    },
    {
        "item": "The Song of Achilles",
        "author": "Madeline Miller",
        "category": "Fiction",
        "catalog": "Fiction shelf",
        "item_code": "BK-0007",
        "item_price": Decimal("17.00"),
        "isbn": "9780062060624",
        "badge": "",
        "item_quantity": 20,
    },
    {
        "item": "The House in the Cerulean Sea",
        "author": "TJ Klune",
        "category": "Fiction",
        "catalog": "Fiction shelf",
        "item_code": "BK-0008",
        "item_price": Decimal("18.00"),
        "isbn": "9781250217288",
        "badge": "",
        "item_quantity": 16,
    },
]


def add_sample_books(apps, schema_editor):
    Category = apps.get_model("bookstore", "Category")
    Item = apps.get_model("bookstore", "Item")
    database = schema_editor.connection.alias

    for sample in SAMPLE_BOOKS:
        category, _ = Category.objects.using(database).get_or_create(
            category_name=sample["category"]
        )
        defaults = {
            key: value
            for key, value in sample.items()
            if key != "category"
        }
        Item.objects.using(database).get_or_create(
            item=sample["item"],
            category=category,
            defaults=defaults,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("bookstore", "0004_cart_updated_at_alter_cartitem_cart_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="author",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="item",
            name="catalog",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="item",
            name="item_code",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="item",
            name="isbn",
            field=models.CharField(blank=True, default="", max_length=13),
        ),
        migrations.AddField(
            model_name="item",
            name="badge",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.RunPython(add_sample_books, migrations.RunPython.noop),
    ]