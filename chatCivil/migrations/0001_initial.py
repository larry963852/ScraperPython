# Generated by Django 5.1.3 on 2024-11-14 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Producto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255)),
                ('precio', models.CharField(max_length=50)),
                ('enlace', models.URLField(max_length=500)),
                ('sku', models.CharField(blank=True, max_length=100, null=True)),
                ('imagen', models.URLField(blank=True, max_length=500, null=True)),
                ('fecha_adicion', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
