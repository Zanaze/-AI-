from django import template

register = template.Library()

# 除法过滤器
@register.filter
def div(a, b):
    if b == 0:
        return 0
    return float(a) / float(b)

# 乘法过滤器
@register.filter
def mul(a, b):
    return float(a) * float(b)