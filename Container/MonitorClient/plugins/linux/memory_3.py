import subprocess

def monitor(frist_invoke=1):
    shell_command = 'free| grep "Mem"'
    status,result = subprocess.getstatusoutput(shell_command)
    if status != 0:
        value_dic = {'status':status}
    else:
        value_dic = {}
        #print('---res:',result)
        total,used,free,shared,cache,available = result.split()[1:]
        value_dic={
            'total':total,
            'used':used,
            'free':free,
            'shared':shared,
            'cache':cache,
            'available':available,
            'status':status
        }
    return value_dic

if __name__ == '__main__':
    print(monitor())