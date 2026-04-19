from django.db import models


class Student(models.Model):
    GENDER_CHOICES = (
        ('男', '男'),
        ('女', '女'),
    )

    sno = models.CharField(max_length=20, primary_key=True, verbose_name='学号')
    name = models.CharField(max_length=20, verbose_name='姓名')
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, default='男', verbose_name='性别')
    dept = models.CharField(max_length=50, verbose_name='所属院系')
    major = models.CharField(max_length=50, verbose_name='专业')
    grade = models.CharField(max_length=10, verbose_name='年级')
    clazz = models.CharField(max_length=20, verbose_name='班级')
    phone = models.CharField(max_length=11, blank=True, null=True, verbose_name='联系方式')
    add_time = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')

    class Meta:
        verbose_name = '学生信息'
        verbose_name_plural = '学生信息'
        ordering = ['-add_time']

    def __str__(self):
        return f'{self.sno}-{self.name}'


class Admin(models.Model):
    username = models.CharField(max_length=20, primary_key=True, verbose_name='管理员账号')
    password = models.CharField(max_length=50, verbose_name='管理员密码')
    add_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '管理员'
        verbose_name_plural = '管理员'

    def __str__(self):
        return self.username


class StudentUser(models.Model):
    sno = models.CharField(max_length=20, primary_key=True, verbose_name='学号')
    password = models.CharField(max_length=50, verbose_name='登录密码')
    add_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '学生账号'
        verbose_name_plural = '学生账号'

    def __str__(self):
        return self.sno


class StudentScore(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='scores', verbose_name='学生')
    subject = models.CharField(max_length=50, verbose_name='科目')
    score = models.FloatField(verbose_name='成绩')
    add_time = models.DateTimeField(auto_now_add=True, verbose_name='录入时间')

    class Meta:
        verbose_name = '学生成绩'
        verbose_name_plural = '学生成绩'
        ordering = ['subject']
        constraints = [
            models.UniqueConstraint(fields=['student', 'subject'], name='unique_student_subject_score'),
        ]

    def __str__(self):
        return f'{self.student_id}-{self.subject}-{self.score}'
