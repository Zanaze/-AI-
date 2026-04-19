from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

# 直接返回空，解决所有 500 报错
def ok(request):
    return HttpResponse("")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),

    # 这两行一次性干掉所有报错
    path('favicon.ico', ok),
    path('.well-known/appspecific/com.chrome.devtools.json', ok),
]