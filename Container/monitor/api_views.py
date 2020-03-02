from django.shortcuts import render,HttpResponse
import json
from monitor.serializer import ClientHandler
from monitor.backends import data_optimization
from django.views.decorators.csrf import csrf_exempt
from monitor.backends import redis_conn
from Container import settings
from monitor import models
from monitor.serializer import get_host_triggers
from monitor.backends import data_processing

REDIS_OBJ = redis_conn.redis_conn(settings)

def client_config(request,client_id):
    config_obj = ClientHandler(client_id)
    config = config_obj.fetch_configs()

    if config:
        return HttpResponse(json.dumps(config))

@csrf_exempt
def service_report(request):
    print("client data:",request.POST)

    try:
        print('host=%s, services=%s' % (request.POST.get('client_id'),request.POST.get('service_name')))
        data = json.loads(request.POST['data'])
        client_id = request.POST.get('client_id')
        service_name = request.POST.get('service_name')
        #存数据
        data_saveing_obj = data_optimization.DataStore(client_id,service_name,data,REDIS_OBJ)

        #同时触发监控
        host_obj = models.Host.objects.get(id=client_id)
        service_triggers = get_host_triggers(host_obj)

        trigger_handler = data_processing.DataHandler(settings,connect_redis=False)
        for trigger in service_triggers:
            trigger_handler.load_service_data_and_calulating(host_obj,trigger,REDIS_OBJ)
        print("service trigger::",service_triggers)

    except IndexError as e:
        print('------>err:',e)

    return HttpResponse(json.dumps("---report success---"))
#    return HttpResponse(json.dumps('received service data'))    #服务端传回给客户端的数据转为json格式