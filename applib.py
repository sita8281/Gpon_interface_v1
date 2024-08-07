import re
import paramiko
import json
import time



class ClientSSH(object):
    def __init__(self, user, passw, ip):

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname=ip,
                            username=user,
                            password=passw,
                            port=22,
                            allow_agent=False,
                            look_for_keys=False)
        self.ssh = self.client.invoke_shell()
        time.sleep(0.8)
        self.ssh.sendall('idle-timeout 200\n')
        self.ssh.sendall('en\n')
        self.ssh.sendall('config\n')
        self.ssh.sendall('int gpon 0/1\n')

    def __del__(self):
        self.client.close()

    def close_connection(self):
        self.client.close()

    def send_data(self, message):
        self.ssh.sendall(message)

    def ready_recv_data(self):
        return self.ssh.recv_ready()

    def receive_data(self):
        if self.ssh.recv_ready():
            output = self.ssh.recv(50000).decode('utf-8')
            return output
        else:
            return False



def check_deleted_ont(string):
    """
    функция парсит информацию о удалении онушки
    """

    result = re.search(r'Number of ONTs that can be deleted', string)

    if result is None:
        return False
    else:
        if result.group() == 'Number of ONTs that can be deleted':
            return 'ont deleted'
        return 'error'


def check_registration_ont(string):
    """
    функция парсит номер номер онушки после её регистрации
    если не удаётся, тогда возвращает False
    """

    result = re.search(r'(?<=ONTID :)\d{1,3}', string)

    if result is None:
        return False
    else:
        return result.group()



def check_autofind_ont(string):
    """
    функция проверки наличия незареганых ONU на Gpon блоке
    возвращает номер порта в виде строки,
    если не удалось найти информацию о незареганых ONU
    возвращает строку 'onu not found'
    если поступила на вход некорректная информация вернёт False
    """
    result = re.search(r'(?<=F/S/P\s{15}: 0/1/)\d{1,2}|'
                       r'Failure: The automatically found ONTs do not exist', string)

    if result is None:
        return False
    else:
        if result.group() == 'Failure: The automatically found ONTs do not exist':
            return 'onu not found'
        else:
             return result.group()


def parsed_onu_distance(string):
    """
    функция парсинга списка дистанций
    """

    onu_distances = re.findall(r"(?<=ONT distance\(m\)\s{9}:\s)\d+|"
                               r"(?<=ONT distance\(m\)\s{9}:\s)-", string)
    count = 0
    for i in onu_distances:
        if i == '-':
            onu_distances[count] = 0
        onu_distances[count] = int(onu_distances[count])
        count += 1

    return onu_distances


def parsed_onu_distance_(string):
    """
    функция парсинга списка дистанций
    """

    onu_distances = re.findall(r"(?<=ONT distance\(m\)\s{9}:\s)\d+|"
                               r"(?<=ONT distance\(m\)\s{9}:\s)-", string)
    count = 0
    for i in onu_distances:
        if i == '-':
            onu_distances[count] = 0
        onu_distances[count] = int(onu_distances[count])
        count += 1

    return len(onu_distances)


def create_list_info(string, str1):
    """
    функция формирования вложенного списка ONU
    список формата [[id_1, id_2,],[name_1, name_2,],[sn..],[status..]]
    если что то пойдёт не так, то вернёт False
    """

    info_onu = check_crc_id(string, str1)
    list_onu_info = []
    if info_onu:
        numbers = [i for i in range(len(info_onu[0]))]
        for number in numbers:
            lst_onu = [number]
            for l in range(4):
                lst_onu.append(info_onu[l][number])
            list_onu_info.append(lst_onu)
        return list_onu_info
    return False



def check_crc_id(string, str1):
    """
    функция проверки контрольной суммы
    проверяет количество строк после парсинга ONU, и общее количество
    ONU зареганых на Gpon блоке, если совпадает возвращает вложенный список
    формата [[имена всех onu на порту], [их серийники], [их статусы]]
    иначе возвращает False
    """

    check_id = re.search(r"(?<=the total of ONTs are:\s)\d+", string)
    if check_id is not None:
        names = parsed_name(string)
        sn = parsed_sn(string)
        status = parsed_status(string)
        distance = parsed_onu_distance(str1)
        id = parsed_id(string)
        if int(check_id.group()) == len(names) == len(sn) == len(status) == len(distance) == len(id):
            return [names, sn, status, distance, id]
    return False


def parsed_id(string):
    """
    функция парсинга реальных ID онушек
    """

    result = re.findall(r'\d+(?=\s{2}\S{16}\s{2})', string)
    if result:
        digit_id = []
        for i in result:
            digit_id.append(int(i))
        return digit_id
    else:
        return False


def parsed_name(string):
    """
    функция парсинга списка имён ONU
    """

    list_onu_names = []
    list_onu = re.findall(r"0/\s1/\d+\s{5,8}\d+\s+.+", string)
    for onu in list_onu:
        regex = re.findall(r"(?<=\s{4}\d\s{3}).+|"
                           r"(?<=\s{4}\d\d\s{3}).+|"
                           r"(?<=\s{4}\d\d\d\s{3}).+|"
                           r"(?<=\s{4}\d\s{4}).+|"
                           r"(?<=\s{4}\d\d\s{4}).+|"
                           r"(?<=\s{4}\d\d\d\s{4}).+", onu)

        name_onu_2 = re.sub(r"\r", '', regex[0])
        name_onu_1 = re.sub(r"\\", '/', name_onu_2)

        list_onu_names.append(name_onu_1)
    return list_onu_names


def parsed_sn(string):
    """
    парсинг серийников ONU
    """

    list_onu_sn = re.findall(r"[0-9A-Z]{16}", string)
    return list_onu_sn


def parsed_status(string):
    """
    парсинг статусов ONU (online/offline)
    """

    list_onu_status = re.findall(r"online(?=\s+normal)|offline(?=\s+initial)", string)
    return list_onu_status


def user_passw_validation(user, passw):
    """
    Валидация логина и пароля пользователя
    """

    if 16 >= len(user) >= 4:
        if 16 >= len(passw) >= 5:
            regex_user = re.search(r'[0-9A-Za-z_]{4,16}', user)
            regex_passw = re.search(r'[0-9A-Za-z_]{5,16}', passw)
            if regex_user is not None and regex_passw is not None:
                if regex_user.group() == user and regex_passw.group() == passw:
                    return True
    return False


def ip_validation(ip):
    """
    Валидация IP адресса
    """

    ip_valid = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', ip)
    if ip_valid is not None:
        if ip_valid.group() == ip:
            octets = ip_valid.group().split('.')
            for octet in octets:
                if int(octet) > 255:
                    return False
            return True
    return False


def name_onu_validation(name):
    """
    Валидация имени ONU
    """

    if 35 >= len(name) >= 3:
        regex_name = re.search(r'[0-9A-Za-z_()/-]{6,35}', name)
        if regex_name is not None:
            if regex_name.group() == name:
                return True

    return False

def sn_validation(sn):
    """
    Валидация серийного номера
    """

    if len(sn) == 16:
        regex_sn = re.search(r"[0-9A-Z]{16}", sn)
        if regex_sn is not None:
            return True

    return False

def save_data(garage, five_lvl):
    """
    Сохранение Логина, Пароля, IP сервера\n
    в файл connectdata.data
    """

    sys_file = 'connectdata.data'
    dump = [garage, five_lvl]
    with open(sys_file, 'w') as file:
        json.dump(dump, file)
    del dump


def load_data():
    """
    Чтение Логина, Пароля, IP сервера\n
    из файла connectdata.data
    """

    sys_file = 'connectdata.data'
    with open(sys_file, 'r') as file:
        dump = json.load(file)
        return dump[0], dump[1]




def search_service_port(string, number_port, number_onu):
    """
    функция поиска сервис-порта по ID и Номеру порта ONU
    возвращает номер сервис порта в виде строки
    """

    result = re.search(fr'\d+(?=\s+\d+\s+common.+gpon\s0/1\s/{number_port}\s+{number_onu}\D)', string)

    if result is not None:
        return result.group()
    else:
        return False

def search_next_free_index(string):
    """
    функция ищет сервис порт после ответа gpon блока
    на комманду display service-port next-free-index
    """

    result = re.search(r'(?<=Next valid free service virtual port ID:\s)\d+', string)

    if result is not None:
        return result.group()
    else:
        return False


def search_ont_signal(string):
    """
    функция парсинга сигнала онушки
    """

    result = re.search(r'(?<=Rx optical power\(dBm\)\s{18}:\s).\d+.\d+', string)

    if result is None:
        return False
    else:
        return float(result.group())


def search_ont_signal_(string):
    """
    функция парсинга сигнала онушки (немного другая)
    """

    result = re.findall(r'(?<=Rx optical power\(dBm\)\s{18}:\s).\d+.\d+', string)
    if result:
        return len(result)
    else:
        result1 = re.findall(r"Failure: The ONT is not online", string)
        if result1:
            return len(result)
    return 0


def search_ont_offline(string):
    """
    функция парсинга оффлайновых онушек
    """

    result = re.search(r"Failure: The ONT is not online", string)

    if result is None:
        return False
    else:
        return 0


def optical_info_packet(string):
    """
    функция собирает сет информации об ONU
    если удалось получить инфу, то возвращает массив
    если не удалось, то возвращает False
    если ONU в оффлайне, тогда вернёт строку типа: 'onu offline'
    """

    if not string:
        return False

    onu_offline = re.findall(r'Failure: The ONT is not online', string)
    if len(onu_offline) != 0:
        if onu_offline[0] == 'Failure: The ONT is not online':
            return 'onu offline'

    vendor_name = re.findall(r'(?<=Vendor name\s{28}:\s).+', string)
    rx_optical = re.findall(r'(?<=Rx optical power\(dBm\)\s{18}:\s).\d+.\d+', string)
    tx_optical = re.findall(r'(?<=Tx optical power\(dBm\)\s{18}:\s).+', string)
    laser_current = re.findall(r'(?<=Laser bias current\(mA\)\s{17}:\s).+', string)
    temperature = re.findall(r'(?<=Temperature\(C\)\s{25}:\s).+', string)
    voltage = re.findall(r'(?<=Voltage\(V\)\s{29}:\s).+', string)
    ont_rx_optical = re.findall(r'(?<=OLT Rx ONT optical power\(dBm\)\s{10}:\s).+', string)

    return [vendor_name,
            rx_optical,
            tx_optical,
            ont_rx_optical,
            laser_current,
            temperature,
            voltage,
            ]

def default_info_packet(string):
    """
    функция собирает сет default информации об ONU
    если удалось получить инфу, то возвращает массив
    если не удалось, то возвращает False
    """

    if not string:
        return False

    sn = re.findall(r'(?<=SN\s{22}:\s).+', string)
    online_duration = re.findall(r'(?<=ONT\sonline\sduration\s{5}:\s).+', string)
    onu_distance = re.findall(r'(?<=ONT\sdistance\(m\)\s{9}:\s).+', string)
    last_up_time = re.findall(r'(?<=Last\sup\stime\s{12}:\s).+', string)
    last_down_time = re.findall(r'(?<=Last\sdown\stime\s{10}:\s).+', string)
    cpu_load = re.findall(r'(?<=CPU\soccupation\s{10}:\s).+', string)
    memory_load = re.findall(r'(?<=Memory\soccupation\s{7}:\s).+', string)

    return [sn,
            last_up_time,
            last_down_time,
            onu_distance,
            memory_load,
            cpu_load,
            online_duration,
            ]

def sort_distance(index):
    return index[5]

def sort_signals(index):
    return index[4]

def sort_id(index):
    return index[0]

def sort_name(index):
    return index[1]


def test_script():
    client = ClientSSH('root', 'admin', '192.168.255.102')

    client.send_data('display ont info 3 all\n')
    client.send_data('          \n')


    time.sleep(0.3)


    out = ''
    while True:
        result = client.receive_data()
        if result is False:
            break
        else:
            out += result
        time.sleep(0.3)

    print(optical_info_packet(out), default_info_packet(out))


if __name__ == '__main__':
    test_script()