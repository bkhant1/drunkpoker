# Generated by Django 3.0.5 on 2020-05-02 12:56

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Table',
            fields=[
                ('name', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('state', models.CharField(max_length=10000)),
            ],
        ),
    ]
