# Generated by Django 2.2.1 on 2020-02-03 13:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0005_auto_20200203_2107'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actionoperation',
            name='msg_format',
            field=models.TextField(default='Hosteeeeee(HOSTNAME:{hostname},IP:{ip}) \nSERVICE:{service_name}) has issue \nMSG:{msg},TIME:{time}', verbose_name='消息格式'),
        ),
    ]
