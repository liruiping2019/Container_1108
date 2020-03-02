
configs = {
    'HostID':3,
    "Server":"172.16.16.200",
    "ServerPort":8000,
    "url":{
        'get_configs':['api/client/config','get'],
        'service_report':['api/client/service/report/','post'],
    },
    'RequestTimeout':30,
    'ConfigUpdateInterval':300,
}