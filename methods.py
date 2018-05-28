import requests
import datetime
import psutil
import config
import persistence
import time

last_notification = 0
first_alarm = True
storage = persistence.Persistence()

def sizeof_fmt(num):
    for x in [' bytes',' KB',' MB',' GB',' TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0

def processMessage(message):
    if "text" in message:
        processTextMessage(message)

def processTextMessage(message):
    text = message["text"]

    if text.startswith("/"):
        processCommandMessage(message)

def processCommandMessage(message):
    text = message["text"]

    if " " in text:
        command, parameter = text.split(" ", 1)
    else:
        command = text
        parameter = ""

    if "@" in command:
        command, botname = command.split("@", 1)
        if botname.lower() != config.NAME.lower():
            return

    if command.lower() == "/start":
        commandStart(message, parameter)
    elif command.lower() == "/stop":
        commandStop(message)
    elif command.lower() == "/help":
        commandHelp(message)
    elif command.lower() == "/uptime":
        commandUptime(message)
    elif command.lower() == "/cpu":
        commandCpu(message)
    elif command.lower() == "/ram":
        commandRam(message)
    elif command.lower() == "/swap":
        commandSwap(message)
    elif command.lower() == "/users":
        commandUsers(message)
    elif command.lower() == "/disks":
        commandDisks(message)
    else:
        sendTextMessage(message["chat"]["id"], "Saya tidak paham dengan perintah " +str(command))

def _sendMessage(chat_id, text, parse_mode=None):
    j = {
        "chat_id" : chat_id,
        "text" : text
    }

    if parse_mode is not None:
        j["parse_mode"] = parse_mode

    r = requests.post(config.API_URL + "sendMessage", json=j)

    result = r.json()
    if not result["ok"]:
        print(result)

def sendTextMessage(chat_id, text):
    _sendMessage(chat_id, text)

def sendAuthMessage(chat_id):
    sendTextMessage(chat_id, "Silahkan Sign In terlebih dahulu. " +
                "Ketik /start <password> untuk Sign In.")

def startupMessage():
    for id in storage.allUsers():
        sendTextMessage(id, "Selamat Datang Di Layanan Chat Bot. " +
                "Ketik /start <password> untuk Sign In.")

def shutdownMessage():
    for id in storage.allUsers():
        sendTextMessage(id, "Shutting Down.")

def sendToAll(text):
    for id in storage.allUsers():
        sendTextMessage(id, text)

def commandStart(message, parameter):
    chat_id = message["chat"]["id"]
    if storage.isRegisteredUser(chat_id):
        sendTextMessage(chat_id, "Anda telah Sign In. Terima Kasih. " +
                "Ketik /help untuk Informasi Selanjutnya.")
    else:
        if parameter.strip() == config.PASSWORD:
            storage.registerUser(chat_id)
            sendTextMessage(chat_id, "Terima Kasih Sudah Sign In. " +
                "Ketik /help untuk Informasi Selanjutnya.")
        else:
            sendTextMessage(chat_id, "Silahkan Masukkan Password yang Benar. " +
                "Ketik /start <password> untuk Sign In.")

def commandStop(message):
    chat_id = message["chat"]["id"]
    if storage.isRegisteredUser(chat_id):
        storage.unregisterUser(chat_id)
        sendTextMessage(chat_id, "Anda telah Sign Out. Anda tidak akan lagi menerima pesan apa pun dari saya.")
    else:
        sendAuthMessage(chat_id)

def commandHelp(message):
    chat_id = message["chat"]["id"]
    sendTextMessage(chat_id, config.NAME + """
Sistem Monitoring Server

/uptime - Uptime Usage
/cpu - CPU Usage
/ram - RAM Usage
/swap - SWAP Usage
/users - Users Aktif
/disks - Disks Usage

Untuk mengakhiri Sistem Monitoring Server Ketikan
/stop - Sign Out dari Sistem Monitoring Server
""")

def commandUptime(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " * UPTIME *\n"
    try:
        text += "Uptime: {0}\n".format(str(datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())))
    except BaseException as be:
        text += "Gagal mendapatkan Informasi Uptime: {0}".format(str(be))

    sendTextMessage(chat_id, text)

def commandCpu(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " * CPU *\n"
    try:
        text += "CPU: {0} %\n".format(psutil.cpu_percent())
    except BaseException as be:
        text += "Gagal mendapatkan Informasi CPU: {0}".format(be)

    sendTextMessage(chat_id, text)

def commandRam(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " * RAM *\n"
    try:
        text += "RAM: {0} % (free: {1})\n".format(psutil.virtual_memory().percent,sizeof_fmt(psutil.virtual_memory().available))
    except BaseException as be:
        text += "Gagal mendapatkan Informasi RAM: {0}".format(be)

    sendTextMessage(chat_id, text)

def commandSwap(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " * SWAP *\n"
    try:
        text += "Swap: {0} % (free: {1})".format(psutil.swap_memory().percent,sizeof_fmt(psutil.swap_memory().free))
    except BaseException as be:
        text += "Gagal mendapatkan Informasi SWAP: {0}".format(be)

    sendTextMessage(chat_id, text)    

def commandUsers(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " * USERS *\n"
    try:
        users = psutil.users()
        for user in users:
            text += "{0}@{1} {2}\n".format(user.name, user.host, str(datetime.datetime.fromtimestamp(user.started)))
    except BaseException as be:
        text += "Gagal mendapatkan Informasi User: {0}".format(be)

    sendTextMessage(chat_id, text)

def commandDisks(message):
    chat_id = message["chat"]["id"]
    if not storage.isRegisteredUser(chat_id):
        sendAuthMessage(chat_id)
        return

    text = " * DISKS *\n"
    num = 0
    try:
        for dev in psutil.disk_partitions(config.ALL_DISKS):
            num += 1
            if len(dev.device) == 0: continue
            usage = psutil.disk_usage(dev.mountpoint)
            text += "{0} ({1}) {2} % (free: {3})\n".format(dev.device
                , dev.mountpoint
                , usage.percent
                , sizeof_fmt(usage.free)
                )
    except BaseException as be:
        text += "Gagal mendapatkan Informasi Disks: {0}".format(be)

    sendTextMessage(chat_id, text)
    
def alarms():
    global last_notification
    now = time.time()
    global first_alarm

    if config.ENABLE_NOTIFICATIONS and (now - last_notification > config.NOTIFCATION_INTERVAL):
        text = "Alarm!\n"
        should_send = False

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        if cpu > config.NOTIFY_CPU_PERCENT:
            text += "CPU: {0} %\n".format(cpu)
            should_send = True
        if ram > config.NOTIFY_RAM_PERCENT:
            text += "RAM: {0} %\n".format(ram)
            should_send = True
        if first_alarm:
            first_alarm = False
            should_send = False
        if should_send:
            last_notification = now
            for id in storage.allUsers():
                sendTextMessage(id, text)
