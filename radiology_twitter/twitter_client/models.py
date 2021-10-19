from django.db import models

class Hashtag(models.Model):
    name = models.CharField(max_length=200, unique=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"# {str(self.name)}"