from decimal import Decimal

from django.db import migrations


STORE_CATEGORY_ITEMS = {
    "Snacks": [
        {
            "item": "Trail Mix",
            "author": "Cedar Market",
            "item_code": "SN-001",
            "item_price": Decimal("6.25"),
            "isbn": "",
            "badge": "Student favorite",
            "item_quantity": 18,
        },
        {
            "item": "Cinnamon Oat Bites",
            "author": "Cedar Market",
            "item_code": "SN-002",
            "item_price": Decimal("4.75"),
            "isbn": "",
            "badge": "Quick bite",
            "item_quantity": 22,
        },
        {
            "item": "Fruit Leather Sticks",
            "author": "Cedar Market",
            "item_code": "SN-003",
            "item_price": Decimal("3.95"),
            "isbn": "",
            "badge": "Grab-and-go",
            "item_quantity": 30,
        },
    ],
    "Drinks": [
        {
            "item": "Cold Brew",
            "author": "North Brew Co.",
            "item_code": "DR-001",
            "item_price": Decimal("5.50"),
            "isbn": "",
            "badge": "Energy boost",
            "item_quantity": 16,
        },
        {
            "item": "Sparkling Lemonade",
            "author": "North Brew Co.",
            "item_code": "DR-002",
            "item_price": Decimal("4.25"),
            "isbn": "",
            "badge": "Citrus refresh",
            "item_quantity": 20,
        },
        {
            "item": "Iced Tea",
            "author": "North Brew Co.",
            "item_code": "DR-003",
            "item_price": Decimal("4.50"),
            "isbn": "",
            "badge": "Classic favorite",
            "item_quantity": 18,
        },
    ],
    "Stationery": [
        {
            "item": "Premium Notebook",
            "author": "Paper & Pine",
            "item_code": "ST-001",
            "item_price": Decimal("8.50"),
            "isbn": "",
            "badge": "Best seller",
            "item_quantity": 14,
        },
        {
            "item": "Mechanical Pencil Set",
            "author": "Paper & Pine",
            "item_code": "ST-002",
            "item_price": Decimal("6.00"),
            "isbn": "",
            "badge": "Smooth write",
            "item_quantity": 25,
        },
        {
            "item": "Sticky Note Pack",
            "author": "Paper & Pine",
            "item_code": "ST-003",
            "item_price": Decimal("4.95"),
            "isbn": "",
            "badge": "Desk essential",
            "item_quantity": 28,
        },
    ],
    "Exam Supplies": [
        {
            "item": "Blue Book Exam Pad",
            "author": "Campus Essentials",
            "item_code": "EX-001",
            "item_price": Decimal("7.25"),
            "isbn": "",
            "badge": "Exam ready",
            "item_quantity": 12,
        },
        {
            "item": "Scientific Calculator Sleeve",
            "author": "Campus Essentials",
            "item_code": "EX-002",
            "item_price": Decimal("9.00"),
            "isbn": "",
            "badge": "Protective",
            "item_quantity": 10,
        },
        {
            "item": "Highlighter Trio",
            "author": "Campus Essentials",
            "item_code": "EX-003",
            "item_price": Decimal("3.50"),
            "isbn": "",
            "badge": "Study kit",
            "item_quantity": 35,
        },
    ],
    "Art Supplies": [
        {
            "item": "Watercolor Set",
            "author": "Studio North",
            "item_code": "AS-001",
            "item_price": Decimal("14.00"),
            "isbn": "",
            "badge": "Artist pick",
            "item_quantity": 9,
        },
        {
            "item": "Sketchbook Pack",
            "author": "Studio North",
            "item_code": "AS-002",
            "item_price": Decimal("11.25"),
            "isbn": "",
            "badge": "Drawing ready",
            "item_quantity": 13,
        },
        {
            "item": "Brush Kit",
            "author": "Studio North",
            "item_code": "AS-003",
            "item_price": Decimal("12.50"),
            "isbn": "",
            "badge": "Studio staple",
            "item_quantity": 11,
        },
    ],
    "Apparel": [
        {
            "item": "Campus Hoodie",
            "author": "Commonplace Threads",
            "item_code": "AP-001",
            "item_price": Decimal("28.00"),
            "isbn": "",
            "badge": "Campus essential",
            "item_quantity": 8,
        },
        {
            "item": "Cotton Crew Socks",
            "author": "Commonplace Threads",
            "item_code": "AP-002",
            "item_price": Decimal("9.50"),
            "isbn": "",
            "badge": "Everyday wear",
            "item_quantity": 20,
        },
        {
            "item": "Canvas Tote Bag",
            "author": "Commonplace Threads",
            "item_code": "AP-003",
            "item_price": Decimal("18.75"),
            "isbn": "",
            "badge": "Carry all day",
            "item_quantity": 15,
        },
    ],
    "Course Supplies": [
        {
            "item": "Lab Manual Binder",
            "author": "Course Works",
            "item_code": "CS-001",
            "item_price": Decimal("15.50"),
            "isbn": "",
            "badge": "Class ready",
            "item_quantity": 12,
        },
        {
            "item": "USB Drive 32GB",
            "author": "Course Works",
            "item_code": "CS-002",
            "item_price": Decimal("18.00"),
            "isbn": "",
            "badge": "Portable backup",
            "item_quantity": 10,
        },
        {
            "item": "Three-Ring Binder Set",
            "author": "Course Works",
            "item_code": "CS-003",
            "item_price": Decimal("12.25"),
            "isbn": "",
            "badge": "Organized",
            "item_quantity": 17,
        },
    ],
    "Books": [
        {
            "item": "The Midnight Library",
            "author": "Matt Haig",
            "item_code": "BK-001",
            "item_price": Decimal("18.00"),
            "isbn": "9780525559474",
            "badge": "Book club pick",
            "item_quantity": 24,
        },
        {
            "item": "The Thursday Murder Club",
            "author": "Richard Osman",
            "item_code": "BK-002",
            "item_price": Decimal("17.50"),
            "isbn": "9781984880987",
            "badge": "Bestseller",
            "item_quantity": 18,
        },
        {
            "item": "The House in the Cerulean Sea",
            "author": "TJ Klune",
            "item_code": "BK-003",
            "item_price": Decimal("18.00"),
            "isbn": "9781250217288",
            "badge": "Staff pick",
            "item_quantity": 16,
        },
    ],
}


def add_store_category_items(apps, schema_editor):
    Category = apps.get_model("bookstore", "Category")
    Item = apps.get_model("bookstore", "Item")
    database = schema_editor.connection.alias

    for category_name, items in STORE_CATEGORY_ITEMS.items():
        category, _ = Category.objects.using(database).get_or_create(
            category_name=category_name,
        )
        for sample in items:
            defaults = {key: value for key, value in sample.items() if key != "item"}
            Item.objects.using(database).get_or_create(
                item=sample["item"],
                category=category,
                defaults=defaults,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("bookstore", "0010_limit_store_categories"),
    ]

    operations = [
        migrations.RunPython(add_store_category_items, migrations.RunPython.noop),
    ]
