from django.db import migrations, models


ALGEBRA_COVER = "https://covers.openlibrary.org/b/id/15239237-L.jpg"
ENGLISH_COVER = "https://covers.openlibrary.org/b/id/13599778-L.jpg"


def add_textbook_covers(apps, schema_editor):
    Item = apps.get_model("bookstore", "Item")
    database = schema_editor.connection.alias
    Item.objects.using(database).filter(
        item="ALgebra Textbook",
        cover_url="",
    ).update(cover_url=ALGEBRA_COVER)
    Item.objects.using(database).filter(
        item="English Textbook",
        cover_url="",
    ).update(cover_url=ENGLISH_COVER)


def remove_textbook_covers(apps, schema_editor):
    Item = apps.get_model("bookstore", "Item")
    database = schema_editor.connection.alias
    Item.objects.using(database).filter(cover_url=ALGEBRA_COVER).update(cover_url="")
    Item.objects.using(database).filter(cover_url=ENGLISH_COVER).update(cover_url="")


class Migration(migrations.Migration):
    dependencies = [
        ("bookstore", "0006_correct_sample_book_isbn"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="cover_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.RunPython(add_textbook_covers, remove_textbook_covers),
        migrations.RemoveField(
            model_name="item",
            name="catalog",
        ),
    ]