# Generated by Django 3.1.7 on 2021-03-21 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='deal',
            name='address',
            field=models.CharField(default='dublin', max_length=254),
        ),
        migrations.AddField(
            model_name='deal',
            name='website_address',
            field=models.CharField(default='dublin@dublin.com', max_length=254),
        ),
    ]
