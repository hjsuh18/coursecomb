# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-02 06:08
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_auto_20180402_0212'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='course',
            name='evals_url',
        ),
        migrations.RemoveField(
            model_name='course',
            name='rating',
        ),
        migrations.AddField(
            model_name='course',
            name='evals',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=['', ''], size=None),
        ),
    ]