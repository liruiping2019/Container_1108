#_*_coding:utf-8_*_

import time
import pickle
import json
import operator
from monitor.backends import redis_conn
from django.conf import settings
from monitor import models


class DataHandler(object):
    def __init__(self,django_settings,connect_redis=True):
        self.django_settings = django_settings
        self.poll_interval = 3 #每3秒进行一次轮询
        self.config_update_interval = 120 #每120秒重新从数据库加载一次配置数据
        self.config_last_loading_time = time.time()
        self.global_monitor_dic = {}
        self.exit_flag = False
        if connect_redis:
            self.redis = redis_conn.redis_conn(django_settings)

    def looping(self):
        '''
        start looping data
        检测主机服务的数据是否按时汇报，只做基本的检测
        :return:
        '''
        self.update_or_load_configs()   #生成全局的监控配置dic
        count = 0
        while not self.exit_flag:
            print("looping %s".center(50,'-') % count)
            count += 1
            if time.time() - self.config_last_loading_time >= self.config_update_interval:
                print(">>>>>>need update configs ...")
                self.update_or_load_configs()
                print("monitor dic",self.global_monitor_dic)
            if self.global_monitor_dic:
                for h,config_dic in self.global_monitor_dic.items():
                    print('handling host: %s' % h)
                    if config_dic['services'] == {}:
                        print('字典为空，主机未上线......')
                        h.status = 3
                        h.save()
                        continue
                    for service_id,val in config_dic['services'].items():#循环所有要监控的服务
                        service_obj,last_monitor_time = val
                        if time.time() - last_monitor_time >= service_obj.interval:
                            print(">>>>>>service [%s] has reached the monitor interval..." % service_obj)
                            self.global_monitor_dic[h]['services'][service_obj.id][1] = time.time()

                            self.data_point_validation(h,service_obj)   #检测此服务最近汇报的数据
                        else:
                            next_monitor_time = time.time() - last_monitor_time - service_obj.interval
                            print("service [%s] next monitor time is %s" % (service_obj.name,next_monitor_time))

                    if time.time() - self.global_monitor_dic[h]['status_last_check'] >10:
                        trigger_redis_key = "host_%s_trigger_*" % (h.id)
                        trigger_keys = self.redis.keys(trigger_redis_key)
                        if len(trigger_keys) == 0:  #即没有trigger被触发
                            h.status = 1
                            h.save()

            time.sleep(self.poll_interval)

    def update_or_load_configs(self):
        '''
        load monitor configs from Mysql DB
        :return:
        '''
        all_enabled_hosts = models.Host.objects.all()
        for h in all_enabled_hosts:
            if h not in self.global_monitor_dic:
                self.global_monitor_dic[h] = {'services':{},'triggers':{}}
                # self.global_monitor_dic={
                #     'h1':{'services':{'cpu':[cpu_obj,0],
                #                       'mem':[mem_obj,0]
                #                       },
                #           'trigger':{t1:t1_obj,}
                #           }
                # }
            service_list = []
            trigger_list = []
            for group in h.host_groups.select_related():
                for template in group.templates.select_related():
                    service_list.extend(template.services.select_related())
                    trigger_list.extend(template.triggers.select_related())
                for service in service_list:
                    if service.id not in self.global_monitor_dic[h]['services']:
                        self.global_monitor_dic[h]['services'][service.id] = [service,0]
                    else:
                        self.global_monitor_dic[h]['services'][service.id][0] = service
                for trigger in trigger_list:
                    self.global_monitor_dic[h]['triggers'][trigger.id] = trigger

            for template in h.templates.select_related():
                service_list.extend(template.services.select_related())
                trigger_list.extend(template.triggers.select_related())
            for service in service_list:
                if service.id not in self.global_monitor_dic[h]['services']:
                    self.global_monitor_dic[h]['services'][service.id] = [service, 0]
                else:
                    self.global_monitor_dic[h]['services'][service.id][0] = service
            for trigger in trigger_list:
                self.global_monitor_dic[h]['triggers'][trigger.id] = trigger
            #通过self.global_monitor_dic[h]这个时间来确定是否需要更新主机状态
            self.global_monitor_dic[h].setdefault('status_last_check',time.time())

        self.config_last_loading_time = time.time()
        return True

    def data_point_validation(self,host_obj,service_obj):
        '''
        取出该服务存入数据库的最后一个值
        :param host_obj:
        :param service_obj:
        :return:
        '''
        service_redis_key = "StatusData_%s_%s_latest" % (host_obj.id,service_obj.name)
        latest_data_point = self.redis.lrange(service_redis_key,-1,-1)
        if latest_data_point:           #成立则说明redis数据库中存在该服务的数据
            latest_data_point = json.loads(latest_data_point[0].decode())
            print(">>>>>>latest data point %s" % latest_data_point)
            latest_service_data,last_report_time = latest_data_point
            monitor_interval = service_obj.interval + self.django_settings.REPORT_LATE_TOLERANCE_TIME   #容忍延迟时间
            if time.time() - last_report_time > monitor_interval:   #超过监控间隔时间数据仍未发送过来
                no_data_secs = time.time() - last_report_time
                msg = '''Some thing must be wrong with client [%s] , because haven't receive data of service [%s] \
                for [%s]s (interval is [%s])''' % (host_obj.ip_addr,service_obj.name,no_data_secs,monitor_interval)
                self.trigger_notifier(host_obj=host_obj,trigger_id=None,positive_expressions=None,redis_obj=None,msg=msg)

                print(">>>>>>%s" % msg)
                if service_obj.name == 'LinuxAlive':    #监控主机存活的服务
                    host_obj.status = 3
                    host_obj.save()
                else:
                    host_obj.status = 1
                    host_obj.save()
            else:
                #print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
                host_obj.status = 1
                host_obj.save()

        else:
            print(">>>>>>no data for service [%s] host[%s] at all" % (service_obj.name,host_obj.name))
            msg = "no data for service [%s] host[%s] at all..." % (service_obj.name,host_obj.name)
            self.trigger_notifier(host_obj=host_obj,trigger_id=None,positive_expressions=None,redis_obj=None,msg=msg)
            host_obj.status = 5
            host_obj.save()

    def load_service_data_and_calulating(self,host_obj,trigger_obj,redis_obj):
        self.redis = redis_obj
        calc_sub_res_list = []  #先将每个expression的结果计算出来放入这个列表中没最后再统一计算这个列表
        positive_expressions = []   #报警时，让用户知道是哪些条件导致触发器成立了
        expression_res_string = ''  #最终拼成的表达式运算字符串
        for expression in trigger_obj.triggerexpression_set.select_related().order_by('id'):
            print(expression,expression.logic_type)
            expression_process_obj = ExpressionProcess(self,host_obj,expression) #单条表达式处理的实例
            single_expression_res = expression_process_obj.process()    #单条表达式处理方法
            if single_expression_res:
                calc_sub_res_list.append(single_expression_res) #把单条表达式放入表达式结果列表
                if single_expression_res['expression_obj'].logic_type:
                    expression_res_string += str(single_expression_res['calc_res']) + ' '+ single_expression_res['expression_obj'].logic_type + ' '
                else:
                    expression_res_string += str(single_expression_res['calc_res']) + ' '

                #把所有结果为True的expression提出来，报警时你得知道是谁出问题导致了trigger触发
                if single_expression_res['calc_res'] == True:
                    single_expression_res['expression_obj'] = single_expression_res['expression_obj'].id #要存到redis里，数据库对象转成id
                    positive_expressions.append(single_expression_res)
        print("whole trigger res:",trigger_obj.name,expression_res_string)
        if expression_res_string:
            trigger_res = eval(expression_res_string)
            print("whole trigger res:", trigger_res)
            if trigger_res: #触发报警
                print("##############trigger alert:",trigger_obj.severity,trigger_res)
                self.trigger_notifier(host_obj,trigger_obj.id,positive_expressions,self.redis,msg=trigger_obj.name)

    def trigger_notifier(self,host_obj,trigger_id,positive_expressions,redis_obj,msg=None):
        if redis_obj:   #从外部调用时才用的到，为了避免重复调用redis连接
            self.redis = redis_obj
        print(">>>>>>going to send alert msg...............")
        print('trigger_notifier argv:',host_obj,trigger_id,positive_expressions,redis_obj)

        msg_dic = {
            'host_id': host_obj.id,
            'host_name':host_obj.name,
            'host_ip':host_obj.ip_addr,
            'trigger_id': trigger_id,
            'positive_expression': positive_expressions,    #这里存的是实例
            'msg': msg,
            'time': time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),
            'start_time': time.time(),
            'duration': None
        }
        self.redis.publish(self.django_settings.TRIGGER_CHAN, pickle.dumps(msg_dic))    #用pickle转换实例存入redis

        #先把之前的trigger加载回来，获取上次警报的时间，以统计故障持续时间
        trigger_redis_key = "host_%s_trigger_%s" % (host_obj.id,trigger_id)
        old_trigger_data = self.redis.get(trigger_redis_key)
        print("old_trigger_data",old_trigger_data)
        if old_trigger_data:
            old_trigger_data = old_trigger_data.decode()
            trigger_startime = json.loads(old_trigger_data)['start_time']
            msg_dic['start_time'] = trigger_startime
            msg_dic['duration'] = round(time.time() - trigger_startime)

        #在redis中记录这个trigger，前端页面展示时要统计trigger个数
        self.redis.set(trigger_redis_key,json.dumps(msg_dic), 300)  #一个trigger记录5分钟后会自动存入redis

class ExpressionProcess(object):
    '''加载数据并用不同的方法计算'''
    def __init__(self,main_ins,host_obj,expression_obj,specified_item=None):
        self.host_obj = host_obj
        self.expression_obj = expression_obj
        self.main_ins = main_ins
        self.service_redis_key = "StatusData_%s_%s_latest" % (host_obj.id,expression_obj.service.name) #拼出要取出的数据在redis中的key
        self.time_range = self.expression_obj.data_calc_args.split(',')[0]

        print("-------->%s" % self.service_redis_key)

    def process(self):
        '''取出指定时间周期的数据，按照指定的数据处理方法处理数据'''
        data_list = self.load_data_from_redis() #按照用户配置取出数据
        data_calc_func = getattr(self,'get_%s' % self.expression_obj.data_calc_func)
        single_expression_calc_res = data_calc_func(data_list)
        print("---res of single_expression_calc_res ", single_expression_calc_res)
        if single_expression_calc_res:  #确保上面的条件有正确的返回
            res_dic = {
                'calc_res':single_expression_calc_res[0],
                'calc_res_val':single_expression_calc_res[1],
                'expression_obj':self.expression_obj,
                'service_item':single_expression_calc_res[2],
            }

            print(">>>>>>single_expression_calc_res:%s" % single_expression_calc_res)
            return res_dic
        else:
            return False

    def load_data_from_redis(self):
        time_in_sec = int(self.time_range) * 60 #默认多取一分钟数据，多出来的后面会去除
        approximate_data_points = (time_in_sec + 60) / self.expression_obj.service.interval #获取一个大概的数据
        print("approximate dataset nums:",approximate_data_points,time_in_sec)
        data_range_raw = self.main_ins.redis.lrange(self.service_redis_key,-int(approximate_data_points),-1)
        approximate_data_range = [json.loads(i.decode()) for i in data_range_raw] #存的依然是大概的数据
        data_range = []
        for point in approximate_data_range:
            val,saving_time = point
            if time.time() - saving_time < time_in_sec:
                data_range.append(point)
                '''if val:'''

        print(data_range)
        return data_range

    def get_avg(self,data_set):
        clean_data_list = []
        clean_data_dic = {}
        for point in data_set:
            val,save_time = point
            if val:
                if 'data' not in val:
                    clean_data_list.append(val[self.expression_obj.service_index.key])

                else:
                    for k,v in val['data'].items():
                        if k not in clean_data_dic:
                            clean_data_dic[k] = []
                        clean_data_dic[k].append(v[self.expression_obj.service_index.key])

        if clean_data_list:
            clean_data_list = [float(i) for i in clean_data_list]
            avg_res = sum(clean_data_list) / len(clean_data_list)
            print(">>>>>>---avg res:%s" % avg_res)
            return [self.judge(avg_res),avg_res,None]
            print('clean data list:',clean_data_list)
        elif clean_data_dic:
            pass
        else:
            return [False,None,None]

    def judge(self,calculated_val): #比较判断
        calc_func = getattr(operator,self.expression_obj.operator_type)
        return calc_func(calculated_val,self.expression_obj.threshold)

    def get_hit(self,data_set):
        pass






