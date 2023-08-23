# Copyright 2022-2023 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

# Generated by Django 3.2.19 on 2023-08-23 18:58

from django.db import migrations, models


def forward_screenshot_count_zero(apps, schema_editor):
    Document = apps.get_model('se', 'Document')
    Document.objects.filter(screenshot_count__isnull=True).update(screenshot_count=0)


def reverse_screenshot_count_zero(apps, schema_editor):
    Document = apps.get_model('se', 'Document')
    Document.objects.filter(screenshot_count=0).update(screenshot_count=None)


class Migration(migrations.Migration):

    dependencies = [
        ('se', '0005_sosse_1_3_0'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='document',
            name='screenshot_file',
        ),
        migrations.RunPython(forward_screenshot_count_zero, reverse_screenshot_count_zero),
        migrations.AlterField(
            model_name='document',
            name='screenshot_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='document',
            name='has_thumbnail',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='crawlpolicy',
            name='create_thumbnails',
            field=models.BooleanField(default=True, help_text='Create thumbnails to display in search results'),
        ),
        migrations.AlterField(
            model_name='crawlpolicy',
            name='snapshot_html',
            field=models.BooleanField(default=True, help_text='Store pages as HTML and download requisite assets'),
        ),
        migrations.AlterField(
            model_name='crawlpolicy',
            name='take_screenshots',
            field=models.BooleanField(default=False, help_text='Store pages as screenshots'),
        ),
    ]
