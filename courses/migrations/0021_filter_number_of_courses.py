# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-27 03:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0020_remove_combination_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='filter',
            name='number_of_courses',
            field=models.SmallIntegerField(default=0),
        ),
    ]
