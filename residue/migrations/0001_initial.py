# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('protein', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Residue',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('sequence_number', models.SmallIntegerField()),
                ('amino_acid', models.CharField(max_length=1)),
            ],
            options={
                'db_table': 'residue',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ResidueGenericNumber',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('label', models.CharField(max_length=10)),
            ],
            options={
                'db_table': 'generic_number',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ResidueNumberingScheme',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('slug', models.SlugField(max_length=20)),
                ('name', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'residue_numbering_scheme',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ResidueSet',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('residue', models.ManyToManyField(to='residue.Residue')),
            ],
            options={
                'db_table': 'residue_set',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='residuegenericnumber',
            name='scheme',
            field=models.ForeignKey(to='residue.ResidueNumberingScheme'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='residue',
            name='generic_number',
            field=models.ManyToManyField(to='residue.ResidueGenericNumber'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='residue',
            name='protein',
            field=models.ForeignKey(to='protein.Protein'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='residue',
            name='protein_segment',
            field=models.ForeignKey(null=True, to='protein.ProteinSegment'),
            preserve_default=True,
        ),
    ]
