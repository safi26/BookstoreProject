from django.db import migrations


def correct_isbn(apps, schema_editor):
    Item = apps.get_model("bookstore", "Item")
    database = schema_editor.connection.alias
    Item.objects.using(database).filter(
        item="The Very Secret Society of Irregular Witches",
        author="Sangu Mandanna",
        isbn="9780593439358",
    ).update(isbn="9780593439357")


def restore_previous_isbn(apps, schema_editor):
    Item = apps.get_model("bookstore", "Item")
    database = schema_editor.connection.alias
    Item.objects.using(database).filter(
        item="The Very Secret Society of Irregular Witches",
        author="Sangu Mandanna",
        isbn="9780593439357",
    ).update(isbn="9780593439358")


class Migration(migrations.Migration):
    dependencies = [
        ("bookstore", "0005_item_book_metadata_and_samples"),
    ]

    operations = [
        migrations.RunPython(correct_isbn, restore_previous_isbn),
    ]