from django.db import migrations


SEED_PLATFORMY = [
    ("allegro", "https://allegro.pl", "api"),
    ("amazon", "https://amazon.pl", "web"),
]


def seed_platformy(apps, schema_editor):
    Platforma = apps.get_model("products", "Platforma")
    for nazwa, bazowy_url, typ_scrapera in SEED_PLATFORMY:
        Platforma.objects.using(schema_editor.connection.alias).update_or_create(
            nazwa=nazwa,
            defaults={"bazowy_url": bazowy_url, "typ_scrapera": typ_scrapera},
        )


def remove_platformy(apps, schema_editor):
    Platforma = apps.get_model("products", "Platforma")
    Platforma.objects.using(schema_editor.connection.alias).filter(
        nazwa__in=[n for n, _, _ in SEED_PLATFORMY]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_platformy, remove_platformy),
    ]
