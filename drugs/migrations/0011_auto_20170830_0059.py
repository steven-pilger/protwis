# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-08-29 22:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drugs', '0010_drugs_references'),
    ]

    operations = [
        migrations.AlterField(
            model_name='drugs',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='drugs',
            name='references',
            field=models.CharField(max_length=180),
        ),
    ]
