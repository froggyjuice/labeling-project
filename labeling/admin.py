from django.contrib import admin
from .models import User, Batch, Image, LabelingResult

admin.site.register(User)
admin.site.register(Batch)
admin.site.register(Image)
admin.site.register(LabelingResult) 