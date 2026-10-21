from django.db import migrations


STORE_CATEGORIES = [
    "Snacks",
    "Drinks",
    "Stationery",
    "Exam Supplies",
    "Art Supplies",
    "Apparel",
    "Course Supplies",
    "Books",
]


def add_store_categories(apps, schema_editor):
    Category = apps.get_model("bookstore", "Category")
    existing_names = {
        name.casefold()
        for name in Category.objects.using(schema_editor.connection.alias)
        .values_list("category_name", flat=True)
    }
    Category.objects.using(schema_editor.connection.alias).bulk_create(
        [
            Category(category_name=name)
            for name in STORE_CATEGORIES
            if name.casefold() not in existing_names
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        ("bookstore", "0008_sale_saleitem"),
    ]

    operations = [
        migrations.RunPython(add_store_categories, migrations.RunPython.noop),
    ]
