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


def limit_store_categories(apps, schema_editor):
    Category = apps.get_model("bookstore", "Category")
    Item = apps.get_model("bookstore", "Item")
    database = schema_editor.connection.alias
    categories = Category.objects.using(database)

    canonical_ids = {}
    for name in STORE_CATEGORIES:
        matches = list(
            categories.filter(category_name__iexact=name).order_by("pk")
        )
        if matches:
            canonical = matches[0]
            if canonical.category_name != name:
                categories.filter(pk=canonical.pk).update(category_name=name)
        else:
            canonical = categories.create(category_name=name)

        canonical_ids[name.casefold()] = canonical.pk
        for duplicate in matches[1:]:
            Item.objects.using(database).filter(category_id=duplicate.pk).update(
                category_id=canonical.pk
            )
            categories.filter(pk=duplicate.pk).delete()

    books_id = canonical_ids["books"]
    allowed_names = [name.casefold() for name in STORE_CATEGORIES]
    extra_categories = categories.all()
    for name in allowed_names:
        extra_categories = extra_categories.exclude(category_name__iexact=name)

    for category in extra_categories.iterator():
        Item.objects.using(database).filter(category_id=category.pk).update(
            category_id=books_id
        )
        categories.filter(pk=category.pk).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bookstore", "0009_seed_store_categories"),
    ]

    operations = [
        migrations.RunPython(limit_store_categories, migrations.RunPython.noop),
    ]
