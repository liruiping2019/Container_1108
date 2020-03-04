from django.urls import path,include,re_path
from monitor import api_views
from monitor import views

urlpatterns = [
    re_path('client/config/(\d+)/$', api_views.client_config),      #re_path使用正则表达式匹配
    re_path('client/service/report/$',api_views.service_report),
    re_path('hosts/status/$', views.hosts_status, name='get_hosts_status'),
    re_path('groups/status/$', views.hostgroups_status, name='get_hostgroups_status'),
    re_path('graphs/$', views.graphs_generator, name='get_graphs'),
    re_path('triggers_list/$',views.triggers_list,name='get_trigger_list')
]