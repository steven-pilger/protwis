# Generated by Django 2.0.8 on 2019-06-22 11:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('structure', '0019_structure_distance_representative'),
    ]

    operations = [
        migrations.AddField(
            model_name='structure',
            name='class_contact_representative',
            field=models.BooleanField(default=False),
        ),
    ]
