# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-14 20:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('construct', '0009_constructmutation_remark'),
    ]

    operations = [
        migrations.AddField(
            model_name='constructmutation',
            name='residue_id',
            field=models.TextField(null=True),
        ),
    ]
