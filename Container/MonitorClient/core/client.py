import time,json,urllib.request,urllib.parse,threading
from MonitorClient.conf import settings
from MonitorClient.plugins import plugin_api

class ClientHandle(object):
    def __init__(self):
        self.monitored_services = {}

    def load_latest_configs(self):
        request_type = settings.configs['url']['get_configs'][1]
        url = "%s/%s" %(settings.configs['url']['get_configs'][0],settings.configs['HostID'])
        latest_configs = self.url_request(request_type,url)
        latest_configs = json.loads(latest_configs)
        self.monitored_services.update(latest_configs)

    def forever_run(self):
        exit_flag = False
        config_last_update_time = 0

        while not exit_flag:
            if time.time() - config_last_update_time > settings.configs['ConfigUpdateInterval']:
                self.load_latest_configs()
                print("Loaded latest config:",self.monitored_services)
                config_last_update_time = time.time()

            for service_name,val in self.monitored_services['services'].items():
                if len(val) == 2:
                    self.monitored_services['services'][service_name].append(0)
                monitor_interval = val[1]
                last_invoke_time = val[2]
                if time.time() - last_invoke_time > monitor_interval:
                    print(last_invoke_time,time.time())
                    self.monitored_services['services'][service_name][2] = time.time() #更新此服务最后一次更新的时间

                    t = threading.Thread(target=self.invoke_plugin,args=(service_name,val))     #多线程，每个监控项目开启一个线程
                    t.start()
                    print("Going to monitor [%s]" % service_name)

                else:
                    print("Going to monitor [%s] in [%s] secs" %(service_name,monitor_interval-(time.time()-last_invoke_time)))

            time.sleep(1)

    def invoke_plugin(self,service_name,val):
        plugin_name = val[0]
        if hasattr(plugin_api,plugin_name):
            func = getattr(plugin_api,plugin_name)
            plugin_callback = func()

            report_data = {
                'client_id':settings.configs['HostID'],
                'service_name':service_name,
                'data':json.dumps(plugin_callback)
            }

            request_action = settings.configs['url']['service_report'][1]
            request_url = settings.configs['url']['service_report'][0]

            print('---report data:',report_data)
            self.url_request(request_action,request_url,params=report_data)
        else:
            print("\033[31;1mCannot find service [%s]'s plugin name [%s] in plugin_api\033[0m"%(service_name,plugin_name))
        print('--plugin:',val)

    def url_request(self,action,url,**extra_data):
        abs_url = "http://%s:%s/%s" % (settings.configs['Server'],
                                       settings.configs['ServerPort'],
                                       url)
        if action in ('get','GET'):
            print(abs_url,extra_data)
            try:
                req = urllib.request.Request(abs_url,method='GET')
                req_data = urllib.request.urlopen(req,timeout=settings.configs['RequestTimeout'])
                callback = req_data.read()
                return callback
            except urllib.request.URLError as e:
                exit("\033[31;1m%s\033[0m"%e)

        elif action in ('post','POST'):
            try:
                data_encode = urllib.parse.urlencode(extra_data['params'])
                req = urllib.request.Request(url=abs_url,data=data_encode,method='POST')
                res_data = urllib.request.urlopen(req,timeout=settings.configs['RequestTimeout'])
                callback = res_data.read()
                callback = json.loads(callback)
                print("\033[31;1m[%s]:[%s]\033[0m response:\n%s" % (action,abs_url,callback))
                return callback
            except Exception as e:
                print('---exec',e)
                exit("\033[31;1m%s\033[0m"%e)