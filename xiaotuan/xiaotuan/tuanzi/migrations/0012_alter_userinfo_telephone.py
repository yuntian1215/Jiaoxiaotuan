# Generated by Django 3.2.13 on 2022-05-18 18:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tuanzi', '0011_auto_20220519_0213'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userinfo',
            name='telephone',
            field=models.CharField(blank=True, max_length=11),
        ),
    ]