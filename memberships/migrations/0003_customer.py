# Generated by Django 3.1.7 on 2021-03-24 22:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('memberships', '0002_auto_20210321_1450'),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripeid', models.CharField(max_length=255)),
                ('stripe_subscription_id', models.CharField(max_length=255)),
                ('cancel_at_period_end', models.BooleanField(default=False)),
                ('membership', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]