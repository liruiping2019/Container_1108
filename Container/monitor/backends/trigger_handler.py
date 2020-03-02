from monitor.backends import redis_conn
import pickle,time
from monitor import models
from django.core.mail import send_mail
from django.conf import settings

class TriggerHandler(object):
    def __init__(self,django_settings):
        self.django_settings = django_settings
        self.redis = redis_conn.redis_conn(self.django_settings)
        self.alert_counters = {}    #记录每个action的触发报警次数
        '''alert_counters = {
            1:{2:{'counter':0,'last_alert':None},
               4:{'counter':1,'last_alert':None}},  #k是action id，里面的k是主机id，value是
        }'''

    def start_watching(self):
        radio = self.redis.pubsub() #打开收音机
        radio.subscribe(self.django_settings.TRIGGER_CHAN)  #调频，订阅
        radio.parse_response()  #准备接听
        print(">>>>>>******start listening new triggers******")
        self.trigger_count = 0
        while True:
            msg = radio.parse_response()    #阻塞，有数据就会往下走
            self.trigger_consume(msg)

    def trigger_consume(self,msg):
        self.trigger_count +=1
        print(">>>>>>******Got a trigger msg [%s]******" % self.trigger_count)
        trigger_msg = pickle.loads(msg[2])

        action = ActionHandler(trigger_msg,self.alert_counters)
        action.trigger_process()

class ActionHandler(object):
    '''负责把达到报警条件的trigger进行分析，并根据action表中的配置来进行报警'''

    def __init__(self,trigger_data,alert_counter_dic):
        self.trigger_data = trigger_data
        self.alert_counter_dic = alert_counter_dic

    def record_log(self,action_obj,action_operation,host_id,trigger_data):
        '''record alert log into DB'''
        models.EventLog.objects.create(
            event_type = 0,
            host_id = host_id,
            trigger_id = trigger_data.get('trigger_id'),
            log = trigger_data
        )

    def action_sms(self, action_obj, action_operation_obj, host_id, trigger_data):
        print("going to send sms to ",action_operation_obj.notifiers.all())

    def action_email(self,action_obj,action_operation_obj,host_id,trigger_data):
        '''
        sending alert email to who concerns.
        :param action_obj: 触发这个报警的action对象
        :param action_operation_obj: 要报警的动作对象
        :param host_id: 要报警的目标主机
        :param trigger_data: 要报警的数据
        :return:
        '''
        print("要发报警的数据:",self.alert_counter_dic[action_obj.id][host_id])
        print("action email:",action_operation_obj.action_type,action_operation_obj.notifiers,trigger_data)
        notifier_mail_list = [obj.user.email for obj in action_operation_obj.notifiers.all()]
        subject = '级别:%s -- 主机:%s -- 服务:%s' %(trigger_data.get('trigger_id'),
                                              trigger_data.get('host_id'),
                                              trigger_data.get('service_item'))

        send_mail(
            subject,
            action_operation_obj.msg_format.format(hostname=trigger_data.get('host_name'),ip=trigger_data.get('host_ip'),service_name=trigger_data.get('host_name'),msg=trigger_data.get('msg'),time=trigger_data.get('time')),
            settings.DEFAULT_FROM_EMAIL,
            notifier_mail_list,
        )

    def trigger_process(self):
        '''
        分析trigger并报警
        :return:
        '''
        print('Action Processing'.center(50,'-'))

        if self.trigger_data.get('trigger_id') == None:
            print(self.trigger_data)
            if self.trigger_data.get('msg'):
                print(self.trigger_data.get('msg'))
            else:
                print(">>>>>>Invalid trigger data %s<<<<<<" % self.trigger_data)
        else:   #报警触发
            print(">>>>>>%s" % self.trigger_data)
            trigger_id = self.trigger_data.get('trigger_id')
            host_id = self.trigger_data.get('host_id')
            trigger_obj = models.Trigger.objects.get(id=trigger_id)
            actions_set = trigger_obj.action_set.select_related()   #找到这个trigger所关联的action list
            print("action_set:",actions_set)
            matched_action_list = set()
            for action in actions_set:
                #每个action都可以直接包含多个主机或主机组
                for hg in action.host_groups.select_related():
                    for h in hg.host_set.select_related():
                        if h.id == host_id:#这个action适用于此主机
                            matched_action_list.add(action)
                            if action.id not in self.alert_counter_dic:#第一次被触发，先初始化一个action
                                self.alert_counter_dic[action.id] = {}
                            print("action, ",id(action))
                            if h.id not in self.alert_counter_dic[action.id]:#这个主机第一次触发这个action
                                self.alert_counter_dic[action.id][h.id] = {'counter':0,'last_alert':time.time()}
                            else:
                                #如果达到报警触发interval次数，就计数+1
                                if time.time() - self.alert_counter_dic[action.id][h.id]['last_alert'] >= action.interval:
                                    self.alert_counter_dic[action.id][h.id]['counter'] += 1
                                else:
                                    print("没达到alert interval时间，不报警",action.interval,
                                          time.time() - self.alert_counter_dic[action.id][h.id]['last_alert'])

                for host in action.hosts.select_related():
                    if host.id == host_id:
                        matched_action_list.add(action)
                        if action.id not in self.alert_counter_dic:
                            self.alert_counter_dic[action.id] = {}
                        if h.id not in self.alert_counter_dic[action.id]:
                            self.alert_counter_dic[action.id][h.id] = {'counter':0,'last_alert':time.time()}
                        else:
                            if time.time() - self.alert_counter_dic[action.id][h.id]['last_alert'] >= action.interval:
                                self.alert_counter_dic[action.id][h.id]['counter'] += 1
                            else:
                                print("没达到alert interval时间，不报警",action.interval,
                                      time.time() - self.alert_counter_dic[action.id][h.id]['last_alert'])

            print("alert_counter_dic:",self.alert_counter_dic)
            print("matched_action_list:",matched_action_list)
            for action_obj in matched_action_list:
                if time.time() - self.alert_counter_dic[action_obj.id][host_id]['last_alert'] >= action_obj.interval:
                    print("该报警了......",time.time() - self.alert_counter_dic[action_obj.id][host_id]['last_alert'],action_obj.interval)
                    for action_operation in action_obj.operations.select_related().order_by('step'):
                        if action_operation.step > self.alert_counter_dic[action_obj.id][host_id]['counter']:
                            print("###################alert action:%s" % action_operation.action_type,action_operation.notifiers)

                            action_func = getattr(self,'action_%s'% action_operation.action_type)
                            action_func(action_obj,action_operation,host_id,self.trigger_data)

                            #报警完成之后更新报警时间，重新计算alert interval
                            self.alert_counter_dic[action_obj.id][host_id]['last_alert'] = time.time()
                            self.record_log(action_obj,action_operation,host_id,self.trigger_data)

                            break


