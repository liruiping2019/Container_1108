#_*_coding:utf-8_*_

from Container import settings
#from django.conf import settings
import time,json
import copy

class DataStore(object):
    def __init__(self,client_id,service_name,data,redis_obj):
        self.client_id = client_id
        self.service_name = service_name
        self.data = data
        self.redis_conn_obj = redis_obj
        self.process_and_save()

    def get_data_slice(self,lastest_data_key,optimization_interval):
        all_real_data = self.redis_conn_obj.lrange(lastest_data_key,1,-1)
        data_set = []
        for item in all_real_data:
            data = json.loads(item.decode())
            if len(data) == 2:
                service_data, last_save_time = data
                if time.time() - last_save_time <= optimization_interval:
                    data_set.append(data)
                else:
                    pass
        return data_set

    def process_and_save(self):
        print("\033[42;1m---service data ----------\033[0m")
        if self.data['status'] ==0:
            for key,data_series_val in settings.STATUS_DATA_OPTIMIZATION.items():
                data_series_optimize_interval,max_data_point = data_series_val
                data_series_key_in_redis = "StatusData_%s_%s_%s" %(self.client_id,self.service_name,key)
                last_point_from_redis = self.redis_conn_obj.lrange(data_series_key_in_redis,-1,-1)
                if not last_point_from_redis:
                    self.redis_conn_obj.rpush(data_series_key_in_redis,json.dumps([None,time.time()]))
                if data_series_optimize_interval == 0:
                    self.redis_conn_obj.rpush(data_series_key_in_redis,json.dumps([self.data,time.time()]))
                else:
                    last_point_data,last_point_save_time = \
                        json.loads(self.redis_conn_obj.lrange(data_series_key_in_redis,-1,-1)[0].decode())

                    if time.time() - last_point_save_time >= data_series_optimize_interval:
                        lastest_data_key_in_redis = "StatusData_%s_%s_latest" %(self.client_id,self.service_name)
                        print("calulating data for key:\033[31;1m%s\033[0m" %data_series_key_in_redis)
                        #取到了最近n分钟的数据

                        data_set = self.get_data_slice(lastest_data_key_in_redis,data_series_optimize_interval)
                        print('------------------------------len dataset :',len(data_set))
                        if len(data_set)>0:
                            optimized_data = self.get_optimized_data(lastest_data_key_in_redis,data_set)
                            if optimized_data:
                                self.save_optimized_data(data_series_key_in_redis,optimized_data)
                #确保数据在redis中的存储数量不超过settings中指定的值
                if self.redis_conn_obj.llen(data_series_key_in_redis) >= max_data_point:
                    self.redis_conn_obj.lpop(data_series_key_in_redis) #删除最旧的一个数据
        else:
            print("report data is invalid::",self.data)
            raise ValueError

    def save_optimized_data(self,data_series_key_in_redis,optimized_data):
        self.redis_conn_obj.rpush(data_series_key_in_redis,json.dumps([optimized_data,time.time()]))

    def get_optimized_data(self,data_set_key, raw_service_data):
        print("get_optimized_data:",raw_service_data[0] )
        service_data_keys = raw_service_data[0][0].keys()
        first_service_data_point = raw_service_data[0][0]

        optimized_dic = {}
        if 'data' not in service_data_keys:
            for key in service_data_keys:
                optimized_dic[key] = []
            tmp_data_dic = copy.deepcopy(optimized_dic)
            print("tmp data dic:",tmp_data_dic)
            for service_data_item,last_save_time in raw_service_data:
                for service_index,v in service_data_item.items():
                    try:
                        tmp_data_dic[service_index].append(round(float(v),2))
                    except ValueError as e:
                        pass
            #算临时字典中每个指标数据的平均值。。。等
            for service_k,v_list in tmp_data_dic.items():
                print(service_k,v_list)
                avg_res = self.get_average(v_list)
                max_res = self.get_max(v_list)
                min_res = self.get_min(v_list)
                mid_res = self.get_mid(v_list)
                optimized_dic[service_k] = [avg_res,max_res,min_res,mid_res]
                print(service_k, optimized_dic[service_k])
        # else:
        #     for service_item_key,v_dic in first_service_data_point['data'].items():
        #         optimized_dic[service_item_key] = {}
        print("optimized empty dic:", optimized_dic)

        return optimized_dic

    def get_average(self,data_set):
        if len(data_set)>0:
            return round(sum(data_set) / len(data_set))
        else:
            return 0

    def get_max(self,data_set):
        if len(data_set)>0:
            return max(data_set)
        else:
            return 0

    def get_min(self,data_set):
        if len(data_set) >0:
            return min(data_set)
        else:
            return 0

    def get_mid(self,data_set):
        data_set.sort()
        if len(data_set)>0:
            return data_set[int(len(data_set)/2)]
        else:
            return 0
