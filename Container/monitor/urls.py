

from django.conf.urls import url
from django.urls import re_path,include
from monitor import views

urlpatterns = [

    #url(r'^$',views.dashboard ),
    #url(r'^dashboard/$',views.dashboard ,name='dashboard' ),
    re_path('^triggers/$',views.triggers,name='triggers' ),
    re_path('^hosts/$',views.hosts ,name='hosts'),
    re_path('^host_groups/$',views.host_groups ,name='host_groups'),
    re_path('hosts/(\d+)/$',views.host_detail ,name='host_detail'),
    #url(r'graph/$',views.graph ,name='get_graph'),
    re_path('^trigger_list/$',views.trigger_list ,name='trigger_list'),
    #url(r'client/service/report/$',views.service_data_report )

]
