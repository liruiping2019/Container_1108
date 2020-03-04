from django.shortcuts import render

# Create your views here.
#_*_coding:utf8_*_
from django.shortcuts import render,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers

from  Container import settings
import json,time
# Create your views here.
from  monitor.serializer import  ClientHandler,get_host_triggers
import json
from monitor.backends import redis_conn
from monitor.backends import data_optimization
from monitor import models
from monitor.backends import data_processing
from monitor import serializer
from monitor import graphs

import hashlib



REDIS_OBJ = redis_conn.redis_conn(settings)

def dashboard(request):

    return render(request,'monitor/dashboard.html')

def triggers(request):

    return render(request,'monitor/triggers.html')


def hosts(request):
    host_list = models.Host.objects.all()
    print("hosts:",host_list)
    return render(request,'monitor/hosts.html',{'host_list':host_list})

def host_detail(request,host_id):
    host_obj = models.Host.objects.get(id=host_id)
    return render(request,'monitor/host_detail.html',{'host_obj':host_obj})

# def host_detail_old(request,host_id):
#     host_obj = models.Host.objects.get(id=host_id)
#
#     config_obj = ClientHandler(host_obj.id)
#     monitored_services = {
#             "services":{},
#             "sub_services": {} #存储一个服务有好几个独立子服务 的监控,比如网卡服务 有好几个网卡
#         }
#
#     template_list= list(host_obj.templates.select_related())
#
#     for host_group in host_obj.host_groups.select_related():
#         template_list.extend( host_group.templates.select_related() )
#     print(template_list)
#     for template in template_list:
#         #print(template.services.select_related())
#
#         for service in template.services.select_related(): #loop each service
#             print(service)
#             if not service.has_sub_service:
#                 monitored_services['services'][service.name] = [service.plugin_name,service.interval]
#             else:
#                 monitored_services['sub_services'][service.name] = []
#
#                 #get last point from redis in order to acquire the sub-service-key
#                 last_data_point_key = "StatusData_%s_%s_latest" %(host_obj.id,service.name)
#                 last_point_from_redis = REDIS_OBJ.lrange(last_data_point_key,-1,-1)[0]
#                 if last_point_from_redis:
#                     data,data_save_time = json.loads(last_point_from_redis)
#                     if data:
#                         service_data_dic = data.get('data')
#                         for serivce_key,val in service_data_dic.items():
#                             monitored_services['sub_services'][service.name].append(serivce_key)
#
#
#     return render(request,'host_detail.html', {'host_obj':host_obj,'monitored_services':monitored_services})

au_list = []
def hosts_status(request):
    # #请求方与响应方共有的key
    # au_key = "aaabbb"
    # client_au_time = request.META['HTTP_AUTIME']
    #
    # server_au_key = "%s|%s" % (au_key,client_au_time)
    # m = hashlib.md5()
    # m.update(bytes(server_au_key,encoding='utf-8'))
    # authkey = m.hexdigest()
    #
    # client_au_key = request.META['HTTP_AUTHKEY']
    # #验证一
    # server_time = time.time()
    # if server_time - 5 > float(client_au_time):
    #     return HttpResponse("超时！")
    # #验证二
    # if authkey != client_au_key:
    #     return HttpResponse("验证失败！")
    # #验证三
    # if authkey in au_list:
    #     return HttpResponse("验证码已过期！")
    # #将成功登录的key值保存在列表中
    # au_list.append(authkey)

    hosts_data_serializer = serializer.StatusSerializer(request,REDIS_OBJ)  #返回对象
    hosts_data = hosts_data_serializer.by_hosts()       #调用对象中的by_hosts方法，返回host_data_list，即主机状态信息

    return HttpResponse(json.dumps(hosts_data))


def hostgroups_status(request):
    group_serializer = serializer.GroupStatusSerializer(request,REDIS_OBJ)
    group_serializer.get_all_groups_status()

    return HttpResponse('ss')


# def client_configs(request,client_id):
#     print("--->",client_id)
#     config_obj = ClientHandler(client_id)
#     config = config_obj.fetch_configs()
#
#     if config:
#         return HttpResponse(json.dumps(config))

# @csrf_exempt
# def service_data_report(request):
#     if request.method == 'POST':
#         print("---->",request.POST)
#         #REDIS_OBJ.set("test_alex",'hahaha')
#         try:
#             print('host=%s, service=%s' %(request.POST.get('client_id'),request.POST.get('service_name') ) )
#             data =  json.loads(request.POST['data'])
#             #print(data)
#             #StatusData_1_memory_latest
#             client_id = request.POST.get('client_id')
#             service_name = request.POST.get('service_name')
#             #把数据存下来
#             data_saveing_obj = data_optimization.DataStore(client_id,service_name,data,REDIS_OBJ)
#
#             #redis_key_format = "StatusData_%s_%s_latest" %(client_id,service_name)
#             #data['report_time'] = time.time()
#             #REDIS_OBJ.lpush(redis_key_format,json.dumps(data))
#
#             #在这里同时触发监控(在这里触发的好处是什么呢？)
#             host_obj = models.Host.objects.get(id=client_id)
#             service_triggers = get_host_triggers(host_obj)
#
#             trigger_handler = data_processing.DataHandler(settings,connect_redis=False)
#             for trigger in service_triggers:
#                 trigger_handler.load_service_data_and_calulating(host_obj,trigger,REDIS_OBJ)
#             print("service trigger::",service_triggers)
#
#
#             #更新主机存活状态
#             #host_alive_key = "HostAliveFlag_%s" % client_id
#             #REDIS_OBJ.set(host_alive_key,time.time())
#         except IndexError as e:
#             print('----->err:',e)
#
#
#     return HttpResponse(json.dumps("---report success---"))


def graphs_generator(request):

    graphs_generator = graphs.GraphGenerator2(request,REDIS_OBJ)
    graphs_data = graphs_generator.get_host_graph()
    print("graphs_data",graphs_data)
    return HttpResponse(json.dumps(graphs_data))

# def graph_bak(request):
#
#
#     #host_id = request.GET.get('host_id')
#     #service_key = request.GET.get('service_key')
#
#     #print("graph:", host_id,service_key)
#
#     graph_generator = graphs.GraphGenerator(request,REDIS_OBJ)
#     graph_data = graph_generator.get_graph_data()
#     if graph_data:
#         return HttpResponse(json.dumps(graph_data))

def triggers(request):

    return render(request,'monitor/triggers.html')

def triggers_list(request,host_id):          #返回报警事件列表json
    host_obj = models.Host.objects.get(id=host_id)

    alert_list = host_obj.eventlog_set.all().order_by('-date')

    trigger_date = []
    for alert in alert_list:
        temp = {}
        temp['event_type'] = alert.get_event_type_display()
        temp['trigger'] = "service:"+alert.trigger.name+",severity:"+alert.trigger.get_severity_display()
        print(type(alert.trigger))
        temp['log'] = alert.log
        temp['date'] = alert.date
        trigger_date.append(temp)

    #trigger_date = serializers.serialize("json", alert_list)
    #return render(request,'monitor/trigger_list.html',locals())
    return HttpResponse(trigger_date)

def trigger_list(request,host_id):          #前端展示
    #host_id = request.GET.get("by_host_id")
    host_obj = models.Host.objects.get(id=host_id)

    alert_list = host_obj.eventlog_set.all().order_by('-date')

    return render(request,'monitor/trigger_list.html',locals())
    #return HttpResponse(service_triggers)

def host_groups(request):

    host_groups = models.HostGroup.objects.all()
    return render(request,'monitor/host_groups.html',locals())