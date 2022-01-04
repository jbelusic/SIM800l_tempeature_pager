# Imports
import time
import json

# Setup logging.
try:
    import logging
    logger = logging.getLogger(__name__)
except:
    try:
        import logger
    except:
        class Logger(object):
            #level = 'INFO'
            level = 'DEBUG'
            @classmethod
            def debug(cls, text):
                if cls.level == 'DEBUG': print('DEBUG:', text)
            @classmethod
            def info(cls, text):
                print('INFO:', text)
            @classmethod
            def warning(cls, text):
                print('WARN:', text)
        logger = Logger()


class GenericATError(Exception):
    '''
    AT ERRORs
    '''
    pass

class GSM_Modem():
    '''
    Version: v1.4 (17.06.2021)
    \nAuthor: Jadranko Belusic
    \nDescription: Pure Python Class (100%) for driving SIM800L GSM Module
    \nInspired by https://github.com/pythings/Drivers
    \nSMS and CALL driver - AT codes handling
    \nSource: https://www.elecrow.com/wiki/images/2/20/SIM800_Series_AT_Command_Manual_V1.09.pdf
    '''
    
    #--------------------------------------------------------------------------------------------
    # Initialize object
    #--------------------------------------------------------------------------------------------
    def __init__(self,
                 uart               = None,
                 MODEM_PWKEY_PIN    = None,
                 MODEM_RST_PIN      = None,
                 MODEM_POWER_ON_PIN = None,
                 MODEM_TX_PIN       = None,
                 MODEM_RX_PIN       = None,
                 MODEM_UARTNO       = None
                 ):
        '''
        Initialize SIM800L modem object
        '''

        # Pins
        self.MODEM_PWKEY_PIN    = MODEM_PWKEY_PIN
        self.MODEM_RST_PIN      = MODEM_RST_PIN
        self.MODEM_POWER_ON_PIN = MODEM_POWER_ON_PIN
        self.MODEM_TX_PIN       = MODEM_TX_PIN
        self.MODEM_RX_PIN       = MODEM_RX_PIN
        self.MODEM_UARTNO       = MODEM_UARTNO

        # Uart
        self.uart = uart
        
        # Initialized indicator
        self.initialized = False
        
        # AT variables
        self.rst_con  = None
        self.commands = tuple()
        self.master   = None
        
        # Callback procedure
        self.callback = None
        
    #--------------------------------------------------------------------------------------------
    # Set MASTER number
    #--------------------------------------------------------------------------------------------
    def set_master(self, p_master):
        '''
        Set MASTER number
        '''
        
        self.master = p_master
    
    #--------------------------------------------------------------------------------------------
    # Set RESET controller
    #--------------------------------------------------------------------------------------------
    def set_rst_con(self, p_rst_con):
        '''
        Set RESET controller
        '''
        
        self.rst_con = p_rst_con
        
    #--------------------------------------------------------------------------------------------
    # Set ALLOWED AT commands
    #--------------------------------------------------------------------------------------------
    def set_commands(self, p_commands):
        '''
        Set ALLOWED AT commands
        '''
        
        self.commands = p_commands
        
    #--------------------------------------------------------------------------------------------
    # Set Callback procedure
    #--------------------------------------------------------------------------------------------
    def set_callback(self, p_allback):
        '''
        Set CALLBACK procedure
        '''
        
        self.callback = p_callback

    #--------------------------------------------------------------------------------------------
    #  Modem initializer
    #--------------------------------------------------------------------------------------------
    def initialize(self):
        '''
        SIM800L modem initialize
        '''

        logger.debug('Initializing modem...')

        if not self.uart:
            from machine import (UART, Pin)

            # Pin initialization
            MODEM_PWKEY_PIN_OBJ    = Pin(self.MODEM_PWKEY_PIN, Pin.OUT)    if self.MODEM_PWKEY_PIN    else None
            MODEM_RST_PIN_OBJ      = Pin(self.MODEM_RST_PIN, Pin.OUT)      if self.MODEM_RST_PIN      else None
            MODEM_POWER_ON_PIN_OBJ = Pin(self.MODEM_POWER_ON_PIN, Pin.OUT) if self.MODEM_POWER_ON_PIN else None
            #MODEM_TX_PIN_OBJ = Pin(self.MODEM_TX_PIN, Pin.OUT) # Not needed as we use MODEM_TX_PIN
            #MODEM_RX_PIN_OBJ = Pin(self.MODEM_RX_PIN, Pin.IN)  # Not needed as we use MODEM_RX_PIN

            # Status setup
            if MODEM_PWKEY_PIN_OBJ:
                MODEM_PWKEY_PIN_OBJ.value(0)
            if MODEM_RST_PIN_OBJ:
                MODEM_RST_PIN_OBJ.value(1)
            if MODEM_POWER_ON_PIN_OBJ:
                MODEM_POWER_ON_PIN_OBJ.value(1)

            # Setup UART
            #self.uart = UART(1, 9600, timeout=1000, rx=self.MODEM_TX_PIN, tx=self.MODEM_RX_PIN)
            self.uart = UART(self.MODEM_UARTNO, 9600, timeout=1000, rx=self.MODEM_TX_PIN, tx=self.MODEM_RX_PIN)
        
        # Disable echo, check if ready         
        self._check_ready()
        # Delete old messages and set the GSM Module in SMS mode
        self._prepare_sms()

    #--------------------------------------------------------------------------------------------
    # SMS prepare
    #--------------------------------------------------------------------------------------------
    def _check_ready(self):
        '''
        Disable ECHO and set initialized to True
        '''
        
        time.sleep(1.5)
        # Test AT commands
        logger.debug("------ Step START -------")
        self.uart.write(b'ATE0\r\n') # Disable ECHO
        time.sleep(1)
        tst = self.uart.readline() # Clear buf
        if tst is not None:
            logger.debug(tst.decode('utf-8').strip())
        tst = self.uart.readline() # Clear buf
        if tst is not None:
            logger.debug(tst.decode('utf-8').strip())
        
        if not tst or tst in (None, b""):
            self.uart.write(b'ATE0\r\n') # Disable ECHO
            time.sleep(.3)
            tst = self.uart.readline()
            if tst is not None:
                logger.debug(tst.decode('utf-8').strip())
            tst = self.uart.readline()
            if tst is not None:
                logger.debug(tst.decode('utf-8').strip())
        
        if tst == b'OK\r\n':
            self.initialized = True 
            logger.debug('Ok, modem is ready and accepting commands')
            logger.debug('------------')
    
    #--------------------------------------------------------------------------------------------
    # SMS prepare
    #--------------------------------------------------------------------------------------------
    def _prepare_sms(self):
        '''
        Prepare for sending SMS AT commands
        '''

        logger.debug('Preparing SMS')
        
        logger.debug('--------------------')
        
        logger.debug('----- Step 1 AT -------')
        self.uart.write(b''+'AT'+'\r\n')
#        logger.debug(self.uart.readline())
#        logger.debug(self.uart.readline())

        logger.debug('----- Step 2 AT+CMGDA="DEL ALL" -------')
        time.sleep(.3)
        self.uart.write(b''+'AT+CMGDA="DEL ALL"\r\n') # delete all (or "AT+CMGD=1,4\n\r")
#        logger.debug(self.uart.readline())
#        logger.debug(self.uart.readline())

        logger.debug('----- Step 3 AT+CMGF=1 -------')
        time.sleep(.3)
        self.uart.write(b''+'AT+CMGF=1\r\n') # set the GSM Module in SMS mode
#        logger.debug(self.uart.readline())
#        logger.debug(self.uart.readline())

        #logger.debug('----- Step End -------') # Reads all messagess from buffer that is produced by Steps 1-3
        for i in range(6): #6 for all Steps
            x = self.uart.readline()
            if x is not None:
                logger.debug("{} {}".format(i+1, x.decode('utf-8').strip()))
            time.sleep(.1)
            
        logger.debug('End of preparing SMS')
    
    #--------------------------------------------------------------------------------------------
    # SMS send message
    #--------------------------------------------------------------------------------------------
    def send_sms(self, phone_number, text_message):
        '''
        Send SMS AT messages
        '''
        
        logger.debug('Sending SMS to number {} with content: {}'.format(phone_number, text_message))
        self.uart.write('AT'+'\r\n')
        time.sleep(.3)
        self.uart.write('AT+CMGF=1'+'\r\n') # Set TEXT MODE
        time.sleep(.3)
        self.uart.write('AT+CMGS="{}"'.format(phone_number)+'\r\n') # Send SMS Command in Text Mode
        time.sleep(.3)
        self.uart.write('{}'.format(text_message)+'\r\n')
        time.sleep(.3)
        self.uart.write(chr(26)+'\r\n') # After the SMS functions finished we need to send ’26’ to get back to normal mode
        time.sleep(.3)
        #self.uart.write('AT+SAPBR=0,1\r\n') # close UART conn
        #self.uart.write(chr(26)+'\r\n')
        logger.debug('SMS sent')
        
        for i in range(8):
            logger.debug("{} {}".format(i+1, self.uart.readline().decode('utf-8').strip()))
            time.sleep(.1)
        
    #--------------------------------------------------------------------------------------------
    # CALL - dial number - calling MASTER
    #--------------------------------------------------------------------------------------------
    def call(self, dial_number):
        '''
        Calling with AT command
        '''

        for _ in range(9):
            tst = self.uart.readline()
            #rl = str(self.uart.readline().strip())
            #print("rl: {}".format(rl))
            #time.sleep(.1)
            if tst is not None:
                logger.debug(tst.decode('utf-8').strip())
            time.sleep(.1)
        
        logger.debug('Calling...')
        self.uart.write('AT'+'\r\n')
        call_sequence = b'ATD+ ' + dial_number + b';\r\n'; # There must be semicolon (;)
        self.uart.write(b''+call_sequence)
        self.uart.write(chr(26)+'\r\n')
        logger.debug("{}".format(self.uart.read()))
        time.sleep(17) #time.sleep(15)
        self.uart.write('ATH\r\n')
        time.sleep(.3)
        logger.debug("{}".format(self.uart.readline()))
        logger.debug('End call')
    
    #--------------------------------------------------------------------------------------------
    # Read message - listening
    #--------------------------------------------------------------------------------------------
    def listening(self):
        '''
        Listening all incomming AT commands
        '''
        
        sms_or_call_message = None
        try:        
            sms_or_call_message = self.uart.readline() # self.uart.read() # self.uart.read(self.uart.inWaiting()) - clears buffer
            #logger.debug('listening: {}'.format(sms_or_call_message))
            
            ## Incomming SMS or CALL message
            #if sms_or_call_message is None:
            #   #sms_or_call_message = ''
            #   # If no message or call is read
            #   empty_reads = 0
            #   line = None
            #   while True:
            #      line = self.uart.readline()
            #      if not line:
            #          time.sleep(.2)
            #          empty_reads += 1
            #          if empty_reads > 10:
            #              sms_or_call_message = ''
            #              break
            #      else:
            #          sms_or_call_message = line
            #          break
               
            if sms_or_call_message is None:
                sms_or_call_message = ""
                
            if len(sms_or_call_message) > 0:
                sms_or_call_message = sms_or_call_message.decode('utf-8').strip()
                sender_number = "NONE"
                
                if sms_or_call_message.upper() in ('CALL READY', 'SMS READY'):
                    return (sms_or_call_message.upper(), sender_number)
                
                # Incomming SMS message
                # '+CMTI: "SM"' - Unsolicited notification of the SMS arriving
                if '+CMTI: "SM"' in sms_or_call_message:
                    pos = sms_or_call_message.find(':')+7
                    sms_index = sms_or_call_message[pos:]
                    logger.debug("Read sms on position: {}".format(sms_index))
                    self.uart.write('AT+CMGR={}'.format(sms_index)+'\r\n')
                    time.sleep(1) # 3
                    sms_at = self.uart.readline().decode('utf-8').strip()
                    time.sleep(.2)
                    sms_info = self.uart.readline().decode('utf-8').strip()
                    logger.debug("sms info: {}".format(sms_info))
                    time.sleep(.2)                   

                    if '+CMGR: "REC UNREAD"' in sms_info:
                        end_pos_num = sms_info.find(',', sms_info.find(',')+1)-1
                        sender_number = sms_info[21:end_pos_num]
                        sms_text = self.uart.readline().decode('utf-8').strip()
                        logger.debug("Message: {}".format(str(sms_text)))
                        if sms_text and sender_number == self.master:
                            if any(sms_text.startswith(s) for s in self.commands):
                                #SMS Count messages on SIM
                                if sms_text == "CNT":
                                    tmp_index = int(sms_index)-1
                                    sms_text = sms_text + str(tmp_index)
                                logger.debug("New unread SMS text: {}".format(sms_text))
                                delete_previous = int(sms_index) - 1
                                self.uart.write('AT+CMGD='+sms_index+'\r\n') # Delete readed SMS
                                time.sleep(1)
                                self.uart.write(chr(26)+'\r\n')
                                time.sleep(.1)
                                logger.debug('Delete new readed SMS {}'.format(sms_index))
                                if int(sms_index) > 1:
                                    time.sleep(1)
                                    self.uart.write('AT+CMGD={}'.format(delete_previous)+'\r\n')
                                    self.uart.write(chr(26)+'\r\n')
                                    time.sleep(.1)
                                    logger.debug("Deleting previous message index: {}".format(str(delete_previous)))
                                time.sleep(1)
                                return (sms_text, sender_number)
                            
                            elif sms_text and sms_text.startswith(self.rst_con):
                                logger.debug("DEEPRESET")
                                delete_previous = int(sms_index) - 1
                                self.uart.write('AT+CMGD='+sms_index+'\r\n') # Delete readed SMS
                                time.sleep(1)
                                self.uart.write(chr(26)+'\r\n')
                                time.sleep(.1)
                                logger.debug('Delete new readed SMS {}'.format(sms_index))
                                if int(sms_index) > 1:
                                    time.sleep(1)
                                    self.uart.write('AT+CMGD={}'.format(delete_previous)+'\r\n')
                                    self.uart.write(chr(26)+'\r\n')
                                    time.sleep(.1)  
                                    logger.debug("Deleting previous message index: {}".format(str(delete_previous)))
                                time.sleep(1)
                                self.uart.write(chr(26)+'\r\n')
                                time.sleep(.1)
                                logger.debug('Delete new readed SMS {}'.format(sms_index))
                                #print("returning to main with sms text {}".format(sms_text))
                                return (sms_text, sender_number)
                            
                            else:
                                logger.debug("Unknown SMS code")
                                self.uart.write('AT+CMGD='+sms_index+'\r\n') # Delete readed SMS
                                time.sleep(1)
                                self.uart.write(chr(26)+'\r\n')
                                time.sleep(.1)
                                logger.debug('Delete new readed SMS {}'.format(sms_index))
                        
                        elif sms_text and not self.master and str(sms_text) == "MASTER":
                            logger.debug("Set MASTER number {}".format(sender_number))
                            return (sms_text, sender_number)
                        
                        elif sms_text and sender_number != self.master and sms_text.startswith("PLEASERESETME"):
                            logger.debug("PLEASERESETME from number {}".format(sender_number))
                            return (sms_text, sender_number)
                        
                        else:
                            logger.debug("No text message or sender is from restricted number")
                            self.uart.write('AT+CMGD='+sms_index+'\r\n') # Delete readed SMS
                            time.sleep(1)
                            self.uart.write(chr(26)+'\r\n')
                            time.sleep(.1)
                            logger.debug('Delete new readed SMS {}'.format(sms_index))
                
                if 'RING' in sms_or_call_message:
                    logger.debug("-------------------")
                    logger.debug('Ringing...')
                    time.sleep(1.5)
                    self.uart.write('ATH\r\n')
                    time.sleep(.5)
                    logger.debug("{}".format(self.uart.readline().decode('utf-8').strip()))
                    time.sleep(.1)
                    sms_or_call_message = self.uart.readline().decode('utf-8').strip()
                    time.sleep(.4)
                    logger.debug("RING: {}".format(sms_or_call_message))
                    logger.debug('End call')
                
                if '+CLIP:' in sms_or_call_message: # +CLIP se provjerava ako je poziv primljen uz RING
                    end_pos_num = sms_or_call_message.find(',', sms_or_call_message.find(','))-1
                    #caller_number = str(sms_or_call_message[8:21])
                    caller_number = sms_or_call_message[8:end_pos_num].strip()
                    logger.debug("INFO about Caller:")
                    logger.debug("Caller number: {}".format(caller_number))
                    
                    if (caller_number == self.master):
                        logger.debug("Number is allowed! Hello Master!")
                        timeout = 0
                        while True: #self.uart.readline():
                            if str(self.uart.readline()).strip() == "OK" or timeout > 10:
                                break
                            timeout += 1
                        return ("TEMP", caller_number)                     
                    else:
                        logger.debug("Number is not allowed!")
                        timeout = 0
                        while self.uart.readline():
                            if str(self.uart.readline()).strip() == "OK" or timeout > 10:
                                break
                            timeout += 1
                        return ("NONE", caller_number)

            sms_or_call_message = None        
            return ("", "")
        except Exception as e:
            logger.debug("err in listening:"+str(e))
            return ("", "")