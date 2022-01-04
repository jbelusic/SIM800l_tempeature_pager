from GSM_SIM800L import ( GSM_Modem as sms_modem, logger )
from machine     import ( UART, Pin, reset, Timer )
from time        import ( sleep, sleep_ms )
import onewire, ds18x20

logger.level = "DEBUG"

logger.debug("Program je započeo!")

#Garbage collection
gc.enable()

'''
Globalne varijable za uključivanje/isključivanje:
 - global_send_sms    - slanje sms-a ili samo simulacija slanja
 - global_call_mob    - pozivanje ili samo simulacija pozivanja
 - global_check_power - provjera napajanja usb/baterija
 - global_log         - provjera ako postoji log.txt za logiranja u log.txt file
'''
global_send_sms    = True
global_call_mob    = True
global_check_power = False
global_log         = False

# Globalne varijable za vrijeme izvođenja timer-a
global_chk_pwr_tim = 10000 # 10000 ms = 10 s
global_chk_tmp_tim = 7000 # 7000 ms = 7 s

# Iz config filea dohvaćamo podatke o slijedećim varijablama:
conf_file   = "config.txt"
master      = ""
min_temp    = -99.00
max_temp    = 99.00
kod         = 0
cfg_sms_str = ""

# Varijable za izvođenje programa
program_works     = True
program_count     = 0
time_out          = 0
sms_txt           = None
poslati_sms       = False
sleep_time        = .3 #1
end_time          = 90
sms_call_info     = tuple()
temporary_temp1   = None
povratni_sms_call = ""
seeker_number     = ""
ds_deviation      = .5
call_sms_ready    = {"CALL READY":"N", "SMS READY":"N"}
ready             = False
glo_temperature   = None #-99

# Led indikator za rad programa
led = Pin(15,Pin.OUT)
#--------------------------------------------------------------------------------------------
# LED on or off
#--------------------------------------------------------------------------------------------
def ledOnOff():
    global led
    try:
        led_state = led.value()
        swap_state = int(not(led_state))
        led.value(swap_state)
        sleep_ms(250)
    except Exception as e:
        logger.debug("Greška prilikom promjene led statusa ledOnOff: {}".format(str(e)))

ledOnOff()

#--------------------------------------------------------------------------------------------
# Read or refresh config file
#--------------------------------------------------------------------------------------------
def read_refresh_config():
    ledOnOff()
    logger.debug("Otvaram i pregledavam konfig vrijednosti")
    global glo_temperature, conf_file, master, min_temp, max_temp, cfg_sms_str, kod, DEEPRESET
    
    try:
        with open(conf_file,"r") as file:
            for red in file:
                d = red.split("=")
                k = d[0].strip().replace("\r","").replace("\n","").replace("'","") # Prvi podatak (key)
                v = d[1].strip().replace("\r","").replace("\n","").replace("'","") # Drugi podatak (value)
                
                # Punimo varujable config podacima
                if k == "MOB":
                    master = v
                elif k == "MIN":
                    if v == "":
                        v = -99
                    min_temp = round(float(v), 2)
                elif k == "MAX":
                    if v == "":
                        v = 99
                    max_temp = round(float(v), 2)
                    glo_temperature = round(float(v), 2) # Inicijalno postavim glo_temperature na početnu vrijednost da ne sadrži None
                elif k == "KOD":
                    if v == "":
                        v = "0"
                    kod = int(v)
                elif k == "X":
                    DEEPRESET = v
                else:
                    pass  
        
        cfg_sms_str  = "Postavke konfiguracije:\n"
        cfg_sms_str += "Broj za slanje SMS-a i pozivanje: {}".format(master if master else "Broj nije postavljen!") +"\n"
        cfg_sms_str += "Minimalna dozvoljena temperatura: {}".format(min_temp)+" *C\n"
        cfg_sms_str += "Maksimalna dozvoljena temperatura: {}".format(max_temp)+" *C\n"
        #cfg_sms_str += "Trenutno ocitana temperatura: {}".format(glo_temperature)+" *C\n"
        
        logger.debug("Vrijednosti su očitane!\n")
        logger.debug("{}".format(cfg_sms_str))
        
    except Exception as e:
        logger.debug("Error kod čitanje read_refresh_config konfiguracije: " + str(e))
    
    ledOnOff()
    
#--------------------------------------------------------------------------------------------
# Update config file
#--------------------------------------------------------------------------------------------
def update_config(value):
    ledOnOff()
    global conf_file
    
    try:
        temp = ""
        prefix = str(value[0:3])
        
        if value.startswith(prefix):
            temp = str(value[3:])
        if temp == "" and value.startswith("KOD"):
            temp = "0"
                           
        logger.debug("Otvaram i pregledavam konfig vrijednosti za {}".format(conf_file))
        
        x = ""
        l = ""
        with open(conf_file,"r") as file, open(conf_file, "w") as file1:
            for line in file:
                l = str(line)
                x = l
                if prefix in l:
                    x = l.replace(l, prefix+"='"+temp+"'\n")
                if len(x) > 5:
                    sleep(1)
                    file1.write(x)
                l = ""
                x = ""
        
        read_refresh_config()
        
        logger.debug("Config je ažuriran sa vrijednoću " + value)
    except Exception as e:
        logger.debug("Error kod upisa u konfiguraciju: " + str(e))
    ledOnOff()
    
#--------------------------------------------------------------------------------------------
# Log data to file
#--------------------------------------------------------------------------------------------
# Test log
def log_data(p_value):
    if global_log:
        with open("log.txt","a") as file:
            file.write("{}".format(p_value)+"\n")

#--------------------------------------------------------------------------------------------
# Inicijalizacija modema SIM800L
#--------------------------------------------------------------------------------------------
modem = None
# ledOnOff()
# logger.debug("-------------------")
# #logger.debug("Pričekajte, inicijaliziram modem...")
# modem = sms_modem(MODEM_PWKEY_PIN    = 4,
#                   MODEM_RST_PIN      = 5,
#                   MODEM_POWER_ON_PIN = 23,
#                   MODEM_TX_PIN       = 26,
#                   MODEM_RX_PIN       = 27)
# ledOnOff()
# modem.set_rst_con("PLEASERESETME")
# ledOnOff()
# modem.set_commands(("KOD",
#                     "HELP",
#                     "RESET",
#                     "TEST",
#                     "TEMP",
#                     "MAX",
#                     "MIN",
#                     "MASTER",
#                     "INFO",
#                     "CNT"))
# ledOnOff()
# logger.debug("-------------------")
# read_refresh_config()
# logger.debug("-------------------")
# modem.set_master(master) 
# modem.initialize()
# #logger.debug("Modem je inicijaliziran!")
# ledOnOff()
# #modem.prepare_sms()
# #ledOnOff()

def set_SIM800L_modem(uartno=1):
    ledOnOff()
    logger.debug("-------------------")
    #logger.debug("Pričekajte, inicijaliziram modem...")
    my_modem = sms_modem(MODEM_PWKEY_PIN    = 4,
                         MODEM_RST_PIN      = 5,
                         MODEM_POWER_ON_PIN = 23,
                         MODEM_TX_PIN       = 26,
                         MODEM_RX_PIN       = 27,
                         MODEM_UARTNO       = uartno)
    ledOnOff()
    my_modem.set_rst_con("PLEASERESETME")
    ledOnOff()
    my_modem.set_commands(("KOD",
                        "HELP",
                        "RESET",
                        "TEST",
                        "TEMP",
                        "MAX",
                        "MIN",
                        "MASTER",
                        "INFO",
                        "CNT"))
    ledOnOff()
    logger.debug("-------------------")
    read_refresh_config()
    logger.debug("-------------------")
    my_modem.set_master(master) 
    my_modem.initialize()
    logger.debug("Modem je inicijaliziran!")
    log_data("Modem je inicijaliziran!")
    ledOnOff()
    #modem.prepare_sms()
    #ledOnOff()
    return my_modem

if modem:
    del modem
    gc.collect()
modem = set_SIM800L_modem()

#--------------------------------------------------------------------------------------------
# SEND SMS
#--------------------------------------------------------------------------------------------
def send_sms(to_number, sms_poruka):
    ledOnOff()
    try:
        if global_send_sms:
            #logger.debug("modem.send_sms({},{})".format(to_number, sms_poruka))
            modem.send_sms(to_number, sms_poruka)
            sleep(4)
        else:
            logger.debug("modem.send_sms({},{})".format(to_number, sms_poruka))
        ledOnOff()
    except Exception as e:
        ledOnOff()
        logger.debug("send_sms global exception:" + str(e))
    
# Power indikator - if ESP32 is on the wall power then input is HIGH
pwr_usb = Pin(14, Pin.IN) #GPIO14
pwr_usb = Pin(35, Pin.IN) #GPIO35 al ne podržava PULL_UP i PULL_DOWN
last_on_usb = pwr_usb.value()
last_on_usb = 1

timer_check_power = Timer(0) #Timer(-1) # Timer(-1) is virtual timer
def check_power(timer_check_power):
#def check_power():
    try:
        #logger.debug("check_power")
        global last_on_usb, global_check_power, pwr_usb#, modem
        if global_check_power:    
            #log_data("check_power...")
            ledOnOff()
            rad_na_bateriju = "Prekid USB napajanja - Rad na bateriju!"
            rad_na_usb      = "Rad na USB napajanje!"
            #logger.debug("Power:", "USB" if pwr_usb.value() == 1 else "Battery")
            if last_on_usb == 1 and pwr_usb.value() in (0, None):
                log_data("Na bateriji sam, provjerim ponovo...")
                sleep(3)
                ## TODO - uništiti objekt i inicijalizirati ponovo modem
                #if modem:
                #    del modem
                #    gc.collect()
                #log_data("Inicijaliziram modem...")
                #modem = set_SIM800L_modem()
                #sleep(10)
                #
                # Check again after 3 sec if power on USB is ON
                if pwr_usb.value() == 1:
                    log_data("Vratio sam se na struju, ne saljem sms!")
                    pass
                    ## TODO - uništiti objekt i inicijalizirati ponovo modem
                    #if modem:
                    #    del modem
                    #    gc.collect()
                    #log_data("Inicijaliziram modem...")
                    #modem = set_SIM800L_modem()
                    #sleep(10)
                    #
                else:
                    log_data("I dalje sam na bateriji i to je ok a bio sam na struji pa saljem sms!")
                    send_sms(master, rad_na_bateriju)
                    logger.debug(rad_na_bateriju)
                    log_data("poslao sms: "+ rad_na_bateriju)
                    last_on_usb = 0
                    log_data("zavrsio ciklus!\n")
                        
            elif last_on_usb == 0 and pwr_usb.value() == 1:
                log_data("Na struji sam a bio sam na bateriji, provjerim ponovo...")
                # USB power
                sleep(3)
                ## TODO - uništiti objekt i inicijalizirati ponovo modem
                #if modem:
                #    del modem
                #    gc.collect()
                #log_data("Inicijaliziram modem...")
                #modem = set_SIM800L_modem()
                #sleep(10)
                #
                # Check again after 3 sec if power on USB is OFF
                if pwr_usb.value() == 0:
                    log_data("Vratio sam se na bateriju, ne saljem sms!")
                    pass
                    ## TODO - uništiti objekt i inicijalizirati ponovo modem
                    #if modem:
                    #    del modem
                    #    gc.collect()
                    #log_data("Inicijaliziram modem...")
                    #modem = set_SIM800L_modem()
                    #sleep(10)
                    #
                else:
                    log_data("I dalje sam na struji i to je ok a bio sam na bateriji pa saljem sms!")
                    send_sms(master, rad_na_usb)
                    logger.debug(rad_na_usb)
                    log_data("poslao sms: "+rad_na_usb)
                    last_on_usb = 1
                    log_data("zavrsio ciklus!\n")
            else:
                pass #log_data("check_power nepoznato stanje napajanja!!!")
            ledOnOff()    
    except Exception as e:
        ledOnOff()
        logger.debug("Greška prilikom očitanja napajanja: {}".format(str(e)))
        log_data("Generalna greska prilikom ocitanja napajanja: " + str(e))
    ledOnOff()

timer_check_power.init(period=global_chk_pwr_tim, mode=Timer.PERIODIC, callback=check_power)

# Inicijalizacija INPUT temperaturnog senzora DS18B20
ds_pin     = Pin(12)
ds_sensors = None
roms       = None

ledOnOff()
logger.debug("-------------------")

#--------------------------------------------------------------------------------------------
# Scan temperature sensor
#--------------------------------------------------------------------------------------------
def scan_ds_sensors():
    ledOnOff()
    global roms, ds_sensors
    try:
        ds_sensors = ds18x20.DS18X20(onewire.OneWire(ds_pin))
        roms = ds_sensors.scan()
        if len(roms) > 0:
            logger.debug("Pronadjeni DS senzori:" + str(roms))
            return True
        else:
            logger.debug("DS senzori nisu pronadjeni!")
            return False
    except Exception as e:
        logger.debug("scan_ds_sensors global exception:" + str(e))
        return False
    ledOnOff()

#--------------------------------------------------------------------------------------------
# Read temperature sensor
#--------------------------------------------------------------------------------------------
# Očitavanje senzora (podržava više DS18B20 senzora)
def read_ds_sensors():
    ledOnOff()
    global ds_sensors, roms, glo_temperature
    loc_sensors = []
    #glo_temperature = 20 # stavljamo na neku srednju početnu temperaturu da imamo startnu vrijednost ako senzor ne očita
    try:
        ds_sensors.convert_temp()
        sleep_ms(750)
        for rom in roms:
            temp = ds_sensors.read_temp(rom)
            sleep_ms(100)
            #ledOnOff()
            if isinstance(temp, float):
                #msg = round(temp, 2)
                loc_sensors.append( round(temp, 2) )
                glo_temperature = round(temp, 2)
                #logger.debug("Očitavam trenutnu temperaturu: {}".format(temp))
                #return msg
                #return loc_sensors
            else:
                loc_sensors.append(glo_temperature) # Last readed temperature
                
    except Exception as e:
        ledOnOff()
        logger.debug("read_ds_sensors global exception:" + str(e))
        
    return loc_sensors    
    ledOnOff()
    
scn = scan_ds_sensors()
tmp = []
if scn:
    tmp = read_ds_sensors()
#if tmp is not None:
if len(tmp) > 0:
    logger.debug("Trenutna očitana temperatura je {}".format(tmp[0]))
else:
    logger.debug("Error prilikom očitanja trenutne temperature senzora")
ledOnOff()
                
# Timer za očitavanje temperature
timer_check_temperature = Timer(1)
#--------------------------------------------------------------------------------------------
# Temperature read
#--------------------------------------------------------------------------------------------
def timer_temperature_read(timer_check_temperature):
    #logger.debug("timer_temperature_read")
    global glo_temperature
    #glo_temperature = None
    tmp_ds_temp = None
    try:
        tmp_ds_temp = read_ds_sensors()
        if len(tmp_ds_temp) > 0:
            glo_temperature = tmp_ds_temp[0]
    except Exception as e:
        #glo_temperature = None
        pass
    #
    if glo_temperature is None : #and ( glo_temperature  > (max_temp + ds_deviation) ) or ( glo_temperature < (min_temp - ds_deviation) ):
        # Dodatna provjera temperaturnog senzora sa odstupanjem (ds_deviation = 0.5)
        sleep(2)                     
        try:
            tmp_ds_temp = None
            # Pročitati opet vrijednosti sa senzora
            tmp_ds_temp = read_ds_sensors()
            if len(tmp_ds_temp) > 0:
                glo_temperature = tmp_ds_temp[0]
        except Exception as e:
            #glo_temperature = None
            pass
#
timer_check_temperature.init(period=global_chk_tmp_tim, mode=Timer.PERIODIC, callback=timer_temperature_read)

#modem.prepare_sms()

#--------------------------------------------------------------------------------------------
# HARD reset
#--------------------------------------------------------------------------------------------
# Hard reset
#def deep_reset(timer):
def deep_reset():
    ledOnOff()
    global conf_file
    try:
        sleep(.5)
        logger.debug("DEEP RESET")        
        file = open (conf_file, "w")
        file.write("MOB=''\n")
        file.write("MIN='-99'\n")
        file.write("MAX='99'\n")
        file.write("KOD='0'")
        file.close()
        sleep(1)
        logger.debug("Uredjaj se resetira na pocetne postavke. Master broj vise nece biti dostupan.")
        send_sms(master, "Uredjaj se resetira na pocetne postavke. Master broj vise nece biti dostupan.")
        sleep(6)
        reset()
    except:
        logger.debug("deep_reset global error")
        file.close()
    ledOnOff()
        
last_on_usb = 0 if last_on_usb in(0, None) else last_on_usb
log_data("Pokrenut na napajanju: USB" if last_on_usb == 1 else "Pokrenut na napajanju: BATERIJA")

#--------------------------------------------------------------------------------------------
# CALL mobile
#--------------------------------------------------------------------------------------------
def call_mobile(param_master):
    try:
        ledOnOff()
        #global global_call_mob
        #logger.debug("Calling mobile")
        if global_call_mob:
            modem.call(param_master)
        else:
            logger.debug("modem.call({})".format(param_master))
        ledOnOff()
    except Exception as e:
        ledOnOff()
        logger.debug("call_mobile global exception:" + str(e))

if master:
    ledOnOff()
    status_napajanja = "Baterija" if pwr_usb.value() == 0 else "USB"
    #status_napajanja = "USB"
    #cfg_sms_str += "Status napajanja: {}".format(status_napajanja)+"\n"
    #logger.debug(cfg_sms_str + "Status napajanja: {}".format(status_napajanja)+"\n")
    logger.debug("Status napajanja: {}".format(status_napajanja)+"\n")
    logger.debug("-------------------")
    #send_sms(master, "Uredjaj je spreman za rad!")
    #logger.debug("Uredjaj je spreman za rad!")
    #sleep(3)
    ledOnOff()
    
if global_log:
    ledOnOff()
    sleep(1)
    #log_data("-----------------\n")
    sleep(1)
    import os
    try:
        logger.debug("File log test je započeo.")
        lista_datoteka = os.listdir()
        log_data("Zapoceo rad na: USB" if last_on_usb == 1 else "Zapoceo rad na: BATERIJI")
        logger.debug("Fileovi na kontroleru: {}".format(lista_datoteka))
        if "log.txt" in lista_datoteka:
            logger.debug("log.txt file postoji!")
        else:
            logger.debug("log.txt file ne postoji!")
        logger.debug("File log test je završio.")
    except Exception as e:
        logger.debug("General error global_log:"+ str(e))
    ledOnOff()

################################## P R O G R A M ##################################

sleep(2)
logger.debug("-------------------")
#logger.debug("Započinjem program")
ledOnOff()

#--------------------------------------------------------------------------------------------
# MAIN
#--------------------------------------------------------------------------------------------
def main():
    global scn
    if not scn:
        scn = scan_ds_sensors()       
main()

gc.collect()

#--------------------------------------------------------------------------------------------
# MAIN LOOP - PROGRAM
#--------------------------------------------------------------------------------------------
while program_works:
    # Program loop...        
    try:
        #logger.debug("prolaz")
        
        ledOnOff()
        #check_power()
        
        # Slanje poruke samo ako se dogodi greška do te mjere da više ne radi program (ako time_out dosegne 90 puta grešku)
        if time_out >= end_time:
            time_out = 0
            send_sms(master, "Error u programu, započinjem automatsko resetiranje sustava!")
            program_works = False
            if led.value() == 1:
                led.value(0)
            sleep(5)
            reset()
        
        # Dohvaćam temeraturu iz globalne varijable
        temporary_temp1 = glo_temperature
        
        # Ovo sve ide u novu proceduru ako uvedemo threaded service klasu za SIM module
        sms_call_info = modem.listening()
        
        #if "" in sms_call_info:
        #    continue
        
        povratni_sms_call = sms_call_info[0].strip() # SMS content
        seeker_number     = sms_call_info[1].strip() # Sender/Caller number
        
        #logger.debug("Main loop: {}, {}".format(temporary_temp1, sms_call_info))
        
        #if povratni_sms_call == "":
        #    continue
        
        if povratni_sms_call in ("CALL READY", "SMS READY"):
            call_sms_ready[povratni_sms_call] = "Y"
            logger.debug("{} ".format(call_sms_ready))
            logger.debug("{} opcija je spremna za upotrebu".format(povratni_sms_call))
        
        if not ready and (call_sms_ready["CALL READY"] == call_sms_ready["SMS READY"] == "Y"):
            send_sms(master, "Uredjaj je spreman za rad! Trenutna temperatura iznosi {}*C".format(temporary_temp1))
            logger.debug("Započinjem program, uredjaj je spreman za rad! Trenutna temperatura iznosi {}*C".format(temporary_temp1))
            ready = True
            
        #ready = True ####################################################################################
        
        if not ready and program_count == 15:
            ready = True # Postavljam ready i ako nije startao kako treba da ne kočim izvršavanje što za sad nije baš najbolje riješenje
        
        if not ready:
            continue
        
        #logger.debug("Going on...")
        
        if temporary_temp1 is not None:
            if not poslati_sms:
                #logger.debug("Temperatura: {}".format(temporary_temp1))
                #if (temporary_temp1 > max_temp):
                if ( temporary_temp1 > (max_temp + ds_deviation) ):
                    # Temperatura je veća od gornje dozvoljene, šaljem upozorenje
                    call_mobile(master)
                    send_sms(master, "PREVISOKA TEMPERATURA: {} *C \nTemperatura je iznad gornje granice od {} *C \n(Dozvoljeno je odstupanje od 0.5 *C)".format(temporary_temp1, (max_temp + ds_deviation)))
                    logger.debug("Previsoka temperatura")
                    # Da ne šalje stalno SMS, postavljam indikator poslanosti dok se temperatura ne unormali                    
                    poslati_sms = True
                    
                #if (temporary_temp1 < min_temp):
                if ( temporary_temp1 < (min_temp - ds_deviation) ):
                    # Temperatura je manja od donje dozvoljene, šaljem upozorenje
                    call_mobile(master)
                    send_sms(master, "PRENISKA TEMPERATURA: {} *C \nTemperatura je ispod donje granice od {} *C \n(Dozvoljeno je odstupanje od 0.5 *C)".format(temporary_temp1, (min_temp - ds_deviation)))
                    logger.debug("Preniska temperatura")
                    # Da ne šalje stalno SMS, postavljam indikator poslanosti dok se temperatura ne unormali                 
                    poslati_sms = True

            #if poslati_sms and (temporary_temp1 <= max_temp) and (temporary_temp1 >= min_temp):
            if poslati_sms and ( temporary_temp1 <= (max_temp + ds_deviation) ) and (temporary_temp1 >= ( min_temp - ds_deviation ) ):
                # Normalna temperatura je postignuta, ponovo dodajem mogućnost slanja upozorenja               
                send_sms(master, "Temperatura je: {} *C \nSada je u postavljenim granicama od {} *C do {} *C \n(Dozvoljeno je odstupanje od 0.5 *C)".format(temporary_temp1, (min_temp - ds_deviation), (max_temp + ds_deviation)))
                logger.debug("Temperatura je ponovo u granicama dozvoljenih vrijednosti uz odstupanje od 0.5 *C")
                poslati_sms = False
                
        
        #--------------------------------------------------------------------------------------------
        # Reading codes from SIM800L
        #--------------------------------------------------------------------------------------------
        
        #logger.debug("Main loop before reading codes: {}, {}".format(temporary_temp1, povratni_sms_call))
        
        # CNT
        if povratni_sms_call.startswith("CNT"):
            logger.debug("SMS COUNTER")
            sms_count = povratni_sms_call[3:]
            send_sms(seeker_number, "Trenutni broj poruka na SIM kartici: {} poruka!".format(sms_count))
        
        # INFO
        if povratni_sms_call.startswith("INFO"):
            logger.debug("SMS INFO")
            # Poziv ili SMS INFO aktivira slanje INFO-a
            #send_sms(seeker_number, "Temperatura iznosi {} *C (Granice su od {} *C do {} *C)".format(temporary_temp1, min_temp, max_temp))
            status_napajanja = "USB" #status_napajanja = "Baterija" if pwr_usb.value() in (None, 0) else "USB"
            send_sms(seeker_number, cfg_sms_str + "Status napajanja: {}".format(status_napajanja)+"\nTrenutna temperatura: {} *C".format(temporary_temp1)+"\n")
            read_refresh_config()
            
        # MIN
        elif povratni_sms_call.startswith("MIN"):
            logger.debug("SMS MIN")
            # Edit config MIN value
            if seeker_number == master:
                #logger.debug(min_temp)
                update_config(povratni_sms_call) # Postavim globalnu min_temp
                #min_temp = povratni_sms_call[3:]
                send_sms(seeker_number, "Postavljena je nova vrijednost MIN {}".format(min_temp))
        
        # MAX
        elif povratni_sms_call.startswith("MAX"):
            logger.debug("SMS MAX")
            # Edit config MAX value
            if seeker_number == master:
                #logger.debug(max_temp)
                update_config(povratni_sms_call) # Postavim globalnu max_temp
                #max_temp = povratni_sms_call[3:]
                send_sms(seeker_number, "Postavljena je nova vrijednost MAX {}".format(max_temp))
        
        # MASTER
        elif povratni_sms_call.startswith("MASTER"):
            logger.debug("SMS MASTER")
            if not master:
                update_config("MOB"+str(seeker_number)) # Postavljam odmah master globalnu varijablu na broj pošiljatelja
                sleep(1)
                modem.set_master(master) # Uzimam iz config file-a jer se iznad trebao napunit
                sleep(1)
                send_sms(master, "Master broj {} je postavljen".format(master))
            else:
                logger.debug("Master broj je vec postavljen")
                send_sms(seeker_number, "Master broj je vec postavljen")
        
        # TEMP
        elif povratni_sms_call.startswith("TEMP"):
            logger.debug("SMS TEMP")
            if seeker_number == master:
                #if not (temporary_temp1 is None):
                if temporary_temp1 is not None: # Ako je na početku očitana temperatura
                    send_sms(seeker_number, "Trenutna temperatura iznosi {} *C".format(temporary_temp1))
                else:
                    logger.debug("Temperatura nije ispravno očitana")
                    send_sms(seeker_number, "Temperatura nije ispravno izmjerena")
        
        # HELP
        elif povratni_sms_call.startswith("HELP"):
            logger.debug("HELP")
            # Help message string
            help_message = "" \
            +"\n  1. MASTER - postavlja master broj" \
            +"\n  2. INFO - informacije iz konfig. file-a" \
            +"\n  3. TEMP - stanje trenutne temperature" \
            +"\n  4. MIN  - postavi min.temperaturu (npr. MIN18)" \
            +"\n  5. MAX  - postavi max.temperaturu (npr. MAX25)" \
            +"\n  6. KOD  - postavljanje koda uredjaja za DEEP RESET (npr. KOD12345)" \
            +"\n  7. CNT  - Broj poruka na SIM kartici" \
            +"\n  8. PLEASERESETME - resetiranje konfig. file-a uz kod (npr. PLEASERESETME12345)" \
            +"\n  9. TEST - Povratni info o radu sustava"
            send_sms(seeker_number, help_message)
            
        # TEST
        elif povratni_sms_call.startswith("TEST"):
            logger.debug("SMS TEST")
            send_sms(seeker_number, "SMS sustav radi!")

            
        # DEEP RESET from MASTER number
        elif povratni_sms_call.startswith("RESET"):
            logger.debug("RESET")
            if seeker_number == master:
                logger.debug("SMS DEEP RESET")
                #send_sms(seeker_number, "Uredjaj se resetira, master broj vise nece biti dostupan")
                sleep(4)
                if led.value() == 1:
                    led.value(0)
                #deep_reset(timer)
                deep_reset()
            else:
                logger.debug("Greska kod izvrsavanja SMS DEEP RESET")
                send_sms(seeker_number, "Greska kod izvrsavanja SMS DEEP RESET")
                   
        # DEEP RESET WITHOUT MASTER
        elif povratni_sms_call.startswith("PLEASERESETME"):
            logger.debug("PLEASERESETME")
            #print(povratni_sms_call, len(povratni_sms_call))
            if len(povratni_sms_call) == 13:
                resetkod = "0"
            else:
                resetkod = povratni_sms_call[13:]
            #print(resetkod,kod)
            #if (resetkod == 0) or (resetkod in kod):
            if str(resetkod)+"9" == str(kod)+"9":
                logger.debug("SMS DEEP RESET")
                if led.value() == 1:
                    led.value(0)
                #deep_reset(timer)
                send_sms(master, "Zatrazeno je resetiranje uredjaja od strane treceg broja: "+seeker_number)
                sleep(15)
                send_sms(seeker_number, "Zatrazeno je resetiranje uredjaja!")
                sleep(15)
                deep_reset()
            else:
                logger.debug("KOD nije unesen za u SMS za resetiranje uređaja a postoji u config file-u!")
                send_sms(seeker_number, "Greska kod izvrsavanja SMS DEEP RESET")
        
        # KODIRANJE
        elif povratni_sms_call.startswith("KOD"):
            logger.debug("KODIRANJE")
            code_number = povratni_sms_call[3:]
            if seeker_number == master:
                if len(code_number) > 0:
                    update_config(povratni_sms_call)
                    sleep(.5)
                    logger.debug("KOD {} je postavljen".format(code_number))
                    send_sms(master, "KOD {} je postavljen".format(code_number)) # Ovdje implicitno šaljem MASTER-u
                else:
                    logger.debug("KOD nije postavljen jer nije poslan u sms poruci")
                    send_sms(master, "KOD nije postavljen jer nije poslan u sms poruci")
            else:
                logger.debug("KOD {} nije postavljen".format(code_number))
                send_sms(master, "KOD {} nije postavljen".format(code_number))
                
        else:
            pass
            
        #modem.read_the_time()
        
        if gc.mem_free() < 102000:
            gc.collect()
        
        # Clearing temp variables
        time_out          = 0
        temporary_temp1   = None  
        sms_call_info     = tuple()
        povratni_sms_call = ""
        seeker_number     = ""
        
        ledOnOff()
        #ledOnOff()
        #ledOnOff()
        #ledOnOff()
        
    except Exception as e:
        time_out          = time_out + 1
        temporary_temp1   = None
        sms_call_info     = tuple()
        povratni_sms_call = ""
        seeker_number     = ""
        logger.debug("Generalna greška: " + str(e))
        #log_data("Generalna greska main loop: " + str(e))
        if gc.mem_free() < 102000:
            gc.collect()

    program_count += 1

    sleep(sleep_time)
    
    if not hasattr(modem, "master"):
        log_data("Objekt ne postoji!")

timer_check_temperature.deinit()
#timer_check_power.deinit()

logger.debug("Izlaz iz programa")

if led.value() == 1:
    led.value(0)
