# Generated by Django 2.0.1 on 2018-02-21 05:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ihr', '0026_auto_20171018_0841'),
    ]

    operations = [
        migrations.CreateModel(
            name='HegemonyCone',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timebin', models.DateTimeField(db_index=True)),
                ('conesize', models.IntegerField(default=0)),
                ('af', models.IntegerField(default=0)),
                ('asn', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ihr.ASN')),
            ],
        ),
        migrations.AlterIndexTogether(
            name='hegemonycone',
            index_together={('timebin', 'asn', 'af')},
        ),
    ]