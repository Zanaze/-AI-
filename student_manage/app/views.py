import json
import re
from functools import wraps

from django.contrib import messages
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from .models import Admin, Student, StudentScore, StudentUser


PHONE_RE = re.compile(r'^1\d{10}$')
GRADE_RE = re.compile(r'^\d{4}$')
SNO_RE = re.compile(r'^\d{2,20}$')


def login_required_decorator(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_username'):
            messages.error(request, '请先登录管理员账号。')
            return redirect('login')
        return func(request, *args, **kwargs)

    return wrapper


def student_login_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('student_sno'):
            messages.error(request, '请先登录学生账号。')
            return redirect('student_login')
        return func(request, *args, **kwargs)

    return wrapper


def _student_queryset():
    return Student.objects.prefetch_related('scores')


def _normalize_student_form(post_data):
    return {
        'sno': post_data.get('sno', '').strip(),
        'name': post_data.get('name', '').strip(),
        'gender': post_data.get('gender', '').strip(),
        'dept': post_data.get('dept', '').strip(),
        'major': post_data.get('major', '').strip(),
        'grade': post_data.get('grade', '').strip(),
        'clazz': post_data.get('clazz', '').strip(),
        'phone': post_data.get('phone', '').strip(),
    }


def _validate_student_form(data):
    errors = []

    if not data['sno']:
        errors.append('学号不能为空。')
    elif not SNO_RE.match(data['sno']):
        errors.append('学号应为 2 到 20 位数字。')

    if not data['name']:
        errors.append('姓名不能为空。')

    if data['gender'] not in {'男', '女'}:
        errors.append('性别只能选择男或女。')

    if not data['dept']:
        errors.append('所属院系不能为空。')

    if not data['major']:
        errors.append('专业不能为空。')

    if not data['grade']:
        errors.append('年级不能为空。')
    elif not GRADE_RE.match(data['grade']):
        errors.append('年级应为 4 位数字，例如 2024。')

    if not data['clazz']:
        errors.append('班级不能为空。')

    phone = data['phone']
    if phone and not PHONE_RE.match(phone):
        errors.append('联系方式必须是 11 位数字手机号。')

    if not phone:
        data['phone'] = ''

    return errors


def _validate_admin_student_form(data):
    errors = []

    if not data['sno']:
        errors.append('学号不能为空。')

    if not data['phone']:
        data['phone'] = ''

    return errors


def _build_validation_report(student, scores):
    results = []

    def add_result(field, ok, ok_message, error_message):
        results.append({
            'field': field,
            'ok': ok,
            'message': ok_message if ok else error_message,
        })

    add_result('学号', bool(SNO_RE.match(student.sno or '')), '学号格式正确。', '学号应为 2 到 20 位数字。')
    add_result('姓名', bool(student.name), '姓名信息无误。', '姓名不能为空。')
    add_result('性别', student.gender in {'男', '女'}, '性别信息无误。', '性别信息有误，只能为男或女。')
    add_result('院系', bool(student.dept), '院系信息无误。', '院系不能为空。')
    add_result('专业', bool(student.major), '专业信息无误。', '专业不能为空。')
    add_result('年级', bool(GRADE_RE.match(student.grade or '')), '年级信息无误。', '年级格式有误，应为 4 位数字。')
    add_result('班级', bool(student.clazz), '班级信息无误。', '班级不能为空。')
    add_result(
        '联系方式',
        (not student.phone) or bool(PHONE_RE.match(student.phone)),
        '联系方式信息无误。' if student.phone else '未填写联系方式。',
        '联系方式信息有误，必须是 11 位数字手机号。',
    )

    invalid_scores = []
    pass_subjects = []
    fail_subjects = []
    excellent_subjects = []
    weak_subjects = []
    total_score = 0

    for score in scores:
        total_score += score.score
        if 0 <= score.score <= 100:
            if score.score >= 85:
                excellent_subjects.append(f'{score.subject} {score.score:g}')
            if score.score < 70:
                weak_subjects.append(f'{score.subject} {score.score:g}')
            if score.score >= 60:
                pass_subjects.append(f'{score.subject} {score.score:g}')
            else:
                fail_subjects.append(f'{score.subject} {score.score:g}')
        else:
            invalid_scores.append(f'{score.subject} {score.score:g}')

    if scores:
        average = total_score / len(scores)
        highest = max(scores, key=lambda item: item.score)
        lowest = min(scores, key=lambda item: item.score)
        score_gap = highest.score - lowest.score
        excellent_gap = max(0, round(85 - average, 2))
        pass_gap = max(0, round(60 - average, 2))
        if average >= 85:
            average_level = '优秀'
            performance_tag = '整体成绩表现优秀，基础较扎实。'
        elif average >= 75:
            average_level = '良好'
            performance_tag = '整体成绩表现良好，仍有提升空间。'
        elif average >= 60:
            average_level = '合格'
            performance_tag = '整体成绩达到合格线，需要继续巩固。'
        else:
            average_level = '待提升'
            performance_tag = '整体成绩偏弱，建议尽快补强薄弱科目。'

        suggestions = []
        warnings = []
        trend_insights = []

        if average >= 85:
            suggestions.append('平均分大于 85，属于优秀水平，建议继续保持。')
        elif average >= 75:
            suggestions.append('平均分处于良好区间，可重点冲刺优势科目。')
        elif average >= 60:
            suggestions.append('平均分刚达到合格区间，建议优先查漏补缺。')
        else:
            suggestions.append('平均分低于 60，建议尽快制定补习和复盘计划。')

        if excellent_subjects:
            suggestions.append(f"优势科目：{'、'.join(excellent_subjects)}。")
        if weak_subjects:
            suggestions.append(f"薄弱科目：{'、'.join(weak_subjects)}，建议优先提升。")
        if fail_subjects:
            suggestions.append(f"存在不及格科目：{'、'.join(fail_subjects)}。")
        if not student.phone:
            suggestions.append('未填写联系方式，建议补充，避免错过通知。')
        elif not PHONE_RE.match(student.phone):
            suggestions.append('联系方式格式异常，建议尽快修改为 11 位手机号。')

        if score_gap >= 25:
            trend_insights.append(f'最高分与最低分相差 {score_gap:g} 分，存在一定偏科现象。')
            suggestions.append('建议把优势科目的学习方法迁移到薄弱科目，缩小分差。')
        else:
            trend_insights.append(f'最高分与最低分相差 {score_gap:g} 分，科目分布相对均衡。')

        if average < 85:
            trend_insights.append(f'距离“优秀”平均分还差 {excellent_gap:g} 分。')
        else:
            trend_insights.append('当前平均分已达到优秀区间。')

        if average < 60:
            trend_insights.append(f'距离“合格”平均分还差 {pass_gap:g} 分。')

        if len(fail_subjects) >= 2:
            warnings.append('学业预警：当前不及格科目达到 2 门及以上，需要优先补弱。')
        elif len(fail_subjects) == 1:
            warnings.append('学业提醒：当前有 1 门科目不及格，建议尽快针对性复习。')

        if len(weak_subjects) >= 3:
            warnings.append('多门科目低于 70 分，基础稳定性不足。')

        if invalid_scores:
            warnings.append('存在异常成绩数据，请先核对录入结果。')

        if not warnings:
            warnings.append('当前暂无明显学业预警。')

        if average >= 85 and score_gap < 20 and not fail_subjects:
            student_type = '优秀稳健型'
            type_reason = '平均分高，科目差距小，整体表现稳定。'
        elif average >= 75 and score_gap >= 25 and not fail_subjects:
            student_type = '偏科提升型'
            type_reason = '整体成绩不差，但科目差距较大，存在明显偏科。'
        elif average >= 60 and fail_subjects:
            student_type = '临界预警型'
            type_reason = '平均分处于合格边缘，同时存在不及格科目。'
        elif average < 60 or len(fail_subjects) >= 2:
            student_type = '基础薄弱型'
            type_reason = '平均分偏低或多门不及格，当前学习基础较弱。'
        elif average >= 75 and not fail_subjects:
            student_type = '稳定发展型'
            type_reason = '整体成绩较稳定，没有明显失分风险，适合继续拔高。'
        else:
            student_type = '待观察型'
            type_reason = '当前数据暂未呈现特别突出的优势或风险，需要继续观察。'

        type_advice = []
        if student_type == '优秀稳健型':
            type_advice.append('建议保持当前学习节奏，尝试冲击更高层次目标。')
            type_advice.append('可以适度承担竞赛、项目或证书类提升任务。')
        elif student_type == '偏科提升型':
            type_advice.append('建议优先补齐薄弱科目，避免总评被单科拖累。')
            type_advice.append('可复用优势科目的学习方法，建立统一复盘节奏。')
        elif student_type == '临界预警型':
            type_advice.append('建议先保证不及格科目转为及格，再考虑整体拔高。')
            type_advice.append('复习策略应从高频错题和基础知识点开始。')
        elif student_type == '基础薄弱型':
            type_advice.append('建议先建立基础补习计划，按周跟踪学习结果。')
            type_advice.append('优先处理低分和不及格科目，避免风险继续扩大。')
        elif student_type == '稳定发展型':
            type_advice.append('建议继续保持稳定输出，逐步把良好区间提升到优秀区间。')
            type_advice.append('可以为重点课程设定更明确的提分目标。')
        else:
            type_advice.append('建议继续积累数据并保持日常学习节奏。')
            type_advice.append('后续可结合更多成绩记录再细化判断。')

        score_summary = {
            'has_scores': True,
            'count': len(scores),
            'average': round(average, 2),
            'average_level': average_level,
            'performance_tag': performance_tag,
            'highest': highest,
            'lowest': lowest,
            'invalid_scores': invalid_scores,
            'pass_subjects': pass_subjects,
            'fail_subjects': fail_subjects,
            'excellent_subjects': excellent_subjects,
            'weak_subjects': weak_subjects,
            'suggestions': suggestions,
            'warnings': warnings,
            'trend_insights': trend_insights,
            'score_gap': round(score_gap, 2),
            'excellent_gap': excellent_gap,
            'pass_gap': pass_gap,
            'student_type': student_type,
            'type_reason': type_reason,
            'type_advice': type_advice,
        }
    else:
        score_summary = {
            'has_scores': False,
            'count': 0,
            'average': None,
            'average_level': '暂无成绩',
            'performance_tag': '暂未录入成绩，无法判断学习水平。',
            'highest': None,
            'lowest': None,
            'invalid_scores': [],
            'pass_subjects': [],
            'fail_subjects': [],
            'excellent_subjects': [],
            'weak_subjects': [],
            'suggestions': ['暂无成绩数据，建议先录入各科成绩后再进行分析。'],
            'warnings': ['暂无成绩数据，暂不生成学业预警。'],
            'trend_insights': ['暂无成绩数据，无法判断是否偏科或是否接近优秀水平。'],
            'score_gap': None,
            'excellent_gap': None,
            'pass_gap': None,
            'student_type': '待分类',
            'type_reason': '当前没有成绩数据，无法进行学生类型分类。',
            'type_advice': ['建议先录入足够的成绩数据，再进行分类判断。'],
        }

    add_result(
        '成绩数据',
        not invalid_scores,
        '成绩数据范围无误。' if scores else '尚未录入成绩数据。',
        f"以下科目成绩超出 0 到 100 范围：{'、'.join(invalid_scores)}",
    )

    overall_ok = all(item['ok'] for item in results)
    return results, score_summary, overall_ok


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        try:
            admin = Admin.objects.get(username=username, password=password)
        except Admin.DoesNotExist:
            messages.error(request, '账号或密码错误。')
        else:
            request.session['admin_username'] = admin.username
            messages.success(request, '管理员登录成功。')
            return redirect('student_list')
    return render(request, 'login.html')


def logout_view(request):
    request.session.clear()
    messages.success(request, '已退出管理员登录。')
    return redirect('login')


@login_required_decorator
def student_list(request):
    students = _student_queryset().all()
    return render(request, 'student_list.html', {'students': students, 'query_data': {}})


@login_required_decorator
def student_add(request):
    if request.method == 'POST':
        data = _normalize_student_form(request.POST)
        errors = _validate_admin_student_form(data)
        if Student.objects.filter(sno=data['sno']).exists():
            errors.append('该学号已存在。')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'student_add.html', {'form_data': data})

        Student.objects.create(**data)
        StudentUser.objects.get_or_create(sno=data['sno'], defaults={'password': data['sno']})
        messages.success(request, '学生信息添加成功，默认密码已同步为学号。')
        return redirect('student_list')

    return render(request, 'student_add.html', {'form_data': {}})


@login_required_decorator
def student_edit(request, sno):
    student = get_object_or_404(Student, sno=sno)

    if request.method == 'POST':
        data = _normalize_student_form(request.POST)
        data['sno'] = student.sno
        errors = _validate_admin_student_form(data)

        if errors:
            for error in errors:
                messages.error(request, error)
            student_form = student
            for key, value in data.items():
                setattr(student_form, key, value)
            return render(request, 'student_edit.html', {'student': student_form})

        for key, value in data.items():
            if key != 'sno':
                setattr(student, key, value)
        student.save()
        messages.success(request, '学生信息修改成功。')
        return redirect('student_list')

    return render(request, 'student_edit.html', {'student': student})


@login_required_decorator
def student_delete(request, sno):
    student = get_object_or_404(Student, sno=sno)
    StudentUser.objects.filter(sno=sno).delete()
    student.delete()
    messages.success(request, f'学号 {sno} 的学生信息已删除。')
    return redirect('student_list')


@login_required_decorator
def student_query(request):
    query_data = {}
    students = _student_queryset().all()

    if request.method == 'POST':
        sno = request.POST.get('sno', '').strip()
        name = request.POST.get('name', '').strip()
        dept = request.POST.get('dept', '').strip()
        major = request.POST.get('major', '').strip()
        query_data = {'sno': sno, 'name': name, 'dept': dept, 'major': major}

        if sno:
            students = students.filter(sno__icontains=sno)
        if name:
            students = students.filter(name__icontains=name)
        if dept:
            students = students.filter(dept__icontains=dept)
        if major:
            students = students.filter(major__icontains=major)

    return render(request, 'student_list.html', {'students': students, 'query_data': query_data})


@login_required_decorator
def student_stat(request):
    dept_stat = Student.objects.values('dept').annotate(count=Count('sno')).order_by('-count')
    gender_stat = Student.objects.values('gender').annotate(count=Count('sno'))
    total = Student.objects.count()

    dept_list = [item['dept'] for item in dept_stat]
    dept_count = [item['count'] for item in dept_stat]
    gender_list = [item['gender'] for item in gender_stat]
    gender_count = [item['count'] for item in gender_stat]

    return render(
        request,
        'student_stat.html',
        {
            'total': total,
            'dept_stat': dept_stat,
            'gender_stat': gender_stat,
            'dept_list': json.dumps(dept_list, ensure_ascii=False),
            'dept_count': json.dumps(dept_count),
            'gender_list': json.dumps(gender_list, ensure_ascii=False),
            'gender_count': json.dumps(gender_count),
        },
    )


@login_required_decorator
def student_score_manage(request, sno):
    student = get_object_or_404(Student, sno=sno)

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        score_raw = request.POST.get('score', '').strip()

        if not subject:
            messages.error(request, '科目名称不能为空。')
        else:
            try:
                score_value = float(score_raw)
            except ValueError:
                messages.error(request, '成绩必须是数字。')
            else:
                if not 0 <= score_value <= 100:
                    messages.error(request, '成绩必须在 0 到 100 之间。')
                else:
                    StudentScore.objects.update_or_create(
                        student=student,
                        subject=subject,
                        defaults={'score': score_value},
                    )
                    messages.success(request, f'{student.name} 的 {subject} 成绩已保存。')
                    return redirect('student_score_manage', sno=sno)

    return render(
        request,
        'student_score_manage.html',
        {
            'student': student,
            'scores': student.scores.all(),
        },
    )


@login_required_decorator
def student_score_delete(request, score_id):
    score = get_object_or_404(StudentScore, id=score_id)
    sno = score.student_id
    if request.method == 'POST':
        score.delete()
        messages.success(request, '成绩记录已删除。')
    return redirect('student_score_manage', sno=sno)


@login_required_decorator
def student_reset_password(request, sno):
    if request.method == 'POST':
        student = get_object_or_404(Student, sno=sno)
        student_user, _ = StudentUser.objects.get_or_create(sno=sno, defaults={'password': sno})
        student_user.password = sno
        student_user.save(update_fields=['password'])
        messages.success(request, f'{student.name} 的密码已重置为学号。')
    return redirect('student_list')


def student_login(request):
    if request.method == 'POST':
        sno = request.POST.get('sno', '').strip()
        password = request.POST.get('password', '').strip()

        try:
            student = Student.objects.get(sno=sno)
        except Student.DoesNotExist:
            messages.error(request, '该学号不存在，请联系管理员先录入学生信息。')
        else:
            student_user, _ = StudentUser.objects.get_or_create(sno=sno, defaults={'password': sno})
            if password == student_user.password:
                request.session['student_sno'] = student.sno
                request.session['student_name'] = student.name
                messages.success(request, f'欢迎你，{student.name}。')
                return redirect('student_center')
            messages.error(request, '密码错误。默认密码为学号，若已修改请使用新密码。')

    return render(request, 'student_login.html')


def student_logout(request):
    request.session.flush()
    messages.success(request, '已退出学生登录。')
    return redirect('student_login')


@student_login_required
def student_center(request):
    sno = request.session.get('student_sno')
    student = get_object_or_404(Student.objects.prefetch_related('scores'), sno=sno)
    scores = list(student.scores.all())
    _, score_summary, _ = _build_validation_report(student, scores)
    return render(
        request,
        'student_center.html',
        {
            'student': student,
            'scores': scores,
            'score_summary': score_summary,
        },
    )


@student_login_required
def student_ai(request):
    sno = request.session.get('student_sno')
    student = get_object_or_404(Student.objects.prefetch_related('scores'), sno=sno)
    scores = list(student.scores.all())
    validation_results, score_summary, overall_ok = _build_validation_report(student, scores)

    return render(
        request,
        'student_ai.html',
        {
            'student': student,
            'scores': scores,
            'validation_results': validation_results,
            'score_summary': score_summary,
            'overall_ok': overall_ok,
        },
    )


@student_login_required
def student_change_pwd(request):
    if request.method == 'POST':
        sno = request.session.get('student_sno')
        old_pwd = request.POST.get('old_pwd', '').strip()
        new_pwd = request.POST.get('new_pwd', '').strip()
        confirm_pwd = request.POST.get('confirm_pwd', '').strip()

        student_user, _ = StudentUser.objects.get_or_create(sno=sno, defaults={'password': sno})

        if student_user.password != old_pwd:
            messages.error(request, '原密码错误。')
        elif len(new_pwd) < 6:
            messages.error(request, '新密码长度不能少于 6 位。')
        elif new_pwd != confirm_pwd:
            messages.error(request, '两次输入的新密码不一致。')
        elif new_pwd == old_pwd:
            messages.error(request, '新密码不能与原密码相同。')
        else:
            student_user.password = new_pwd
            student_user.save(update_fields=['password'])
            messages.success(request, '密码修改成功，请重新登录。')
            request.session.flush()
            return redirect('student_login')

    return render(request, 'student_change_pwd.html')
