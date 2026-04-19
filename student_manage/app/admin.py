from django.contrib import admin

from .models import Admin, Student, StudentScore, StudentUser


admin.site.register(Admin)
admin.site.register(Student)
admin.site.register(StudentUser)
admin.site.register(StudentScore)
