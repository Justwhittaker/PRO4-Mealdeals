# Generated by Django 3.1.7 on 2021-03-26 00:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('client_profile', '0002_auto_20210326_0044'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deal',
            name='price',
        ),
    ]
