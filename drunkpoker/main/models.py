from django.db import models


class Table(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    state = models.CharField(max_length=10000)
