from django.db import models

class ResumeHistory(models.Model):
    action_type = models.CharField(max_length=100)
    file_name = models.CharField(max_length=255)
    ai_result = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} - {self.file_name}"