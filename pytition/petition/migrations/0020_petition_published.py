# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-02-01 10:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('petition', '0019_auto_20180201_1132'),
    ]

    operations = [
        migrations.AddField(
            model_name='petition',
            name='published',
            field=models.BooleanField(default=False),
        ),
    ]