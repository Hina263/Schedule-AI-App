from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0002_alter_event_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(default='default_user', max_length=100, unique=True)),
                ('default_duration_hours', models.IntegerField(default=1)),
                ('warning_level', models.CharField(
                    choices=[('gentle', '優しい'), ('standard', '標準'), ('strict', '厳しめ')],
                    default='standard',
                    max_length=20,
                )),
                ('remind_minutes_before', models.IntegerField(blank=True, null=True)),
                ('remind_day_before', models.BooleanField(default=False)),
                ('remind_days_before_deadline', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'user_settings',
            },
        ),
    ]
